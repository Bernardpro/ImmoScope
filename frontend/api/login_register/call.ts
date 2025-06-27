// lib/api.ts - Configuration axios
import axios from "axios";
import { NextRequest, NextResponse } from "next/server";

// Create axios instance
const createAxiosMaille = () => {
	return axios.create({
		baseURL: "https://api.homepedia.spectrum-app.cloud",
		responseType: "json",
	});
};

/*curl -X 'POST' \
  'http://localhost:82/user/signup' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "mail": "string@gmail.com",
  "name": "string",
  "password": "stringstringstring"
}' 

curl -X 'POST' \
  'http://localhost:82/user/login' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'grant_type=password&username=string%40gmail.com&password=stringstringstring&scope=&client_id=&client_secret='

*/

export async function useGetLogin(request: NextRequest) {
	try {
		const { firstName, lastName, email, password } = await request.json();

		// Validation
		if (!firstName || !lastName || !email || !password) {
			return NextResponse.json({ error: "Tous les champs sont requis" }, { status: 400 });
		}

		if (password.length < 6) {
			return NextResponse.json({ error: "Le mot de passe doit contenir au moins 6 caractères" }, { status: 400 });
		}

		// Validation email
		const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
		if (!emailRegex.test(email)) {
			return NextResponse.json({ error: "Email invalide" }, { status: 400 });
		}

		const api = createAxiosMaille();

		// Appel au backend FastAPI pour l'inscription
		const backendResponse = await api.post("/user/signup", {
			mail: email,
			name: `${firstName} ${lastName}`,
			password: password,
		});

		// Réponse réussie du backend
		const userData = {
			id: backendResponse.data.id || Date.now(),
			firstName,
			lastName,
			email,
			...backendResponse.data,
		};

		return NextResponse.json(
			{
				message: "Inscription réussie",
				user: userData,
			},
			{ status: 201 },
		);
	} catch (error: any) {
		console.error("Erreur d'inscription:", error);

		// Gestion des erreurs du backend
		if (error.response) {
			const status = error.response.status;
			const message = error.response.data?.detail || "Erreur lors de l'inscription";

			if (status === 400) {
				return NextResponse.json({ error: message }, { status: 400 });
			} else if (status === 409) {
				return NextResponse.json({ error: "Un compte avec cet email existe déjà" }, { status: 409 });
			}
		}

		return NextResponse.json({ error: "Erreur serveur" }, { status: 500 });
	}
}

export async function useGetRegister(request: NextRequest) {
	try {
		const { email, password } = await request.json();

		// Validation basique
		if (!email || !password) {
			return NextResponse.json({ error: "Email et mot de passe requis" }, { status: 400 });
		}

		const api = createAxiosMaille();

		// Préparation des données pour l'appel FastAPI (form-urlencoded)
		const formData = new URLSearchParams();
		formData.append("grant_type", "password");
		formData.append("username", email);
		formData.append("password", password);
		formData.append("scope", "");
		formData.append("client_id", "");
		formData.append("client_secret", "");

		// Appel au backend FastAPI pour la connexion
		const backendResponse = await api.post("/user/login", formData, {
			headers: {
				"Content-Type": "application/x-www-form-urlencoded",
				accept: "application/json",
			},
		});

		// Extraire les données de l'utilisateur et le token
		const { access_token, token_type, ...userData } = backendResponse.data;

		// Créer la réponse avec les données utilisateur
		const response = NextResponse.json({
			message: "Connexion réussie",
			user: {
				email: email,
				...userData,
			},
		});

		// Stocker le token dans un cookie HTTP-only sécurisé
		response.cookies.set("auth-token", access_token, {
			httpOnly: true,
			secure: process.env.NODE_ENV === "production",
			sameSite: "lax",
			maxAge: 60 * 60 * 24 * 7, // 7 jours
			path: "/",
		});

		// Optionnel: stocker le type de token
		response.cookies.set("token-type", token_type || "bearer", {
			httpOnly: true,
			secure: process.env.NODE_ENV === "production",
			sameSite: "lax",
			maxAge: 60 * 60 * 24 * 7,
			path: "/",
		});

		return response;
	} catch (error: any) {
		console.error("Erreur de connexion:", error);

		// Gestion des erreurs du backend
		if (error.response) {
			const status = error.response.status;
			const message = error.response.data?.detail || "Erreur de connexion";

			if (status === 401 || status === 400) {
				return NextResponse.json({ error: "Identifiants invalides" }, { status: 401 });
			}
		}

		return NextResponse.json({ error: "Erreur serveur" }, { status: 500 });
	}
}

/*curl -X 'GET' \
  'http://localhost:82/user/me' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhYWFhQGdtYWlsLmNvbSIsImV4cCI6MTc1MDMyNjAxNCwiaWF0IjoxNzUwMzIyNDE0LCJzY29wZSI6InJlYWQgd3JpdGUifQ.p7N-SuXp_Z6r8mjaWYtrCd_-rW-Q0eTFoOSsLBdg2VY' */

export async function useGetMe(request: NextRequest) {
	try {
		const authHeader = request.headers.get("Authorization");
		if (!authHeader || !authHeader.startsWith("Bearer ")) {
			return NextResponse.json({ error: "Token manquant ou invalide" }, { status: 401 });
		}

		const token = authHeader.split(" ")[1];
		const api = createAxiosMaille();

		// Appel au backend FastAPI pour récupérer les informations de l'utilisateur
		const backendResponse = await api.get("/user/me", {
			headers: {
				Authorization: `Bearer ${token}`,
				accept: "application/json",
			},
		});

		return NextResponse.json(backendResponse.data, { status: 200 });
	} catch (error: any) {
		console.error("Erreur lors de la récupération des informations utilisateur:", error);
		return NextResponse.json({ error: "Erreur serveur" }, { status: 500 });
	}
}
