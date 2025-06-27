"use client";

import React, { useState, createContext, useContext, useEffect } from "react";
import "./layout.scss";
import { useGetLogin } from "@/api/login_register/call";
import { useRouter, useSearchParams } from "next/navigation";
import { useGetArianne } from "@/api/maillage";
import Link from "next/link";

// Types pour l'authentification
interface LoginFormData {
	username: string;
	password: string;
}

interface RegisterFormData {
	firstName: string;
	lastName: string;
	email: string;
	password: string;
	confirmPassword: string;
}

interface ModalProps {
	isOpen: boolean;
	onClose: () => void;
	children: React.ReactNode;
}

interface AuthModalProps {
	isOpen: boolean;
	onClose: () => void;
	onSwitchToRegister?: () => void;
	onSwitchToLogin?: () => void;
}

interface AuthContextType {
	openLogin: () => void;
	openRegister: () => void;
	closeModals: () => void;
	isLoginOpen: boolean;
	isRegisterOpen: boolean;
}

interface RootLayoutProps {
	children: React.ReactNode;
}

// Options pour typeDataDisplay
const DATA_TYPE_OPTIONS = [
	{ value: "reputation", label: "Réputation" },
	{ value: "foncier", label: "Foncier" },
];

// Context pour l'authentification
const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
	const context = useContext(AuthContext);
	if (!context) {
		throw new Error("useAuth must be used within an AuthProvider");
	}
	return context;
};

// Composant Modal de base
function Modal({ isOpen, onClose, children }: ModalProps) {
	if (!isOpen) return null;

	return (
		<div className="modal_overlay" onClick={onClose}>
			<div className="modal_content" onClick={(e) => e.stopPropagation()}>
				<button className="modal_close" onClick={onClose}>
					×
				</button>
				{children}
			</div>
		</div>
	);
}

// Composant de connexion
function LoginModal({ isOpen, onClose, onSwitchToRegister }: AuthModalProps) {
	const [formData, setFormData] = useState<LoginFormData>({
		username: "",
		password: "",
	});
	const [isLoading, setIsLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);

	const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
		setFormData({
			...formData,
			[e.target.name]: e.target.value,
		});
		// Réinitialiser l'erreur quand l'utilisateur tape
		if (error) setError(null);
	};

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		setIsLoading(true);
		setError(null);

		try {
			// Utiliser le bon endpoint pour la connexion (useGetRegister fait la connexion)
			const params = new URLSearchParams();
			params.append("grant_type", "password");
			params.append("username", formData.username);
			params.append("password", formData.password);
			params.append("scope", "");
			params.append("client_id", "");
			params.append("client_secret", "");

			const response = await fetch("http://back:82/user/login", {
				method: "POST",
				headers: {
					"Content-Type": "application/x-www-form-urlencoded",
				},
				body: params.toString(),
			});
			const data = await response.json();

			if (response.ok) {
				console.log("Connexion réussie", data);
				onClose();
				// Redirection ou mise à jour de l'état global
				// Par exemple : router.push('/dashboard') ou updateUser(data.user)
			} else {
				setError(data.error || "Erreur de connexion");
			}
		} catch (error) {
			console.error("Erreur:", error);
			setError("Erreur de connexion au serveur");
		} finally {
			setIsLoading(false);
		}
	};

	return (
		<Modal isOpen={isOpen} onClose={onClose}>
			<div className="auth_form">
				<h2>Connexion</h2>
				<form onSubmit={handleSubmit}>
					{error && <div className="error_message">{error}</div>}
					<div className="form_group">
						<label htmlFor="email">Email</label>
						<input
							type="email"
							id="email"
							name="username"
							value={formData.username}
							onChange={handleChange}
							required
							disabled={isLoading}
						/>
					</div>
					<div className="form_group">
						<label htmlFor="password">Mot de passe</label>
						<input
							type="password"
							id="password"
							name="password"
							value={formData.password}
							onChange={handleChange}
							required
							disabled={isLoading}
						/>
					</div>
					<button type="submit" className="btn_primary btn_full" disabled={isLoading}>
						{isLoading ? "Connexion..." : "Se connecter"}
					</button>
				</form>
				<div className="auth_switch">
					<p>
						Pas encore de compte ?{" "}
						<button type="button" className="link_button" onClick={onSwitchToRegister} disabled={isLoading}>
							S'inscrire
						</button>
					</p>
				</div>
			</div>
		</Modal>
	);
}

// Composant d'inscription
function RegisterModal({ isOpen, onClose, onSwitchToLogin }: AuthModalProps) {
	const [formData, setFormData] = useState<RegisterFormData>({
		firstName: "",
		lastName: "",
		email: "",
		password: "",
		confirmPassword: "",
	});
	const [isLoading, setIsLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);

	const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
		setFormData({
			...formData,
			[e.target.name]: e.target.value,
		});
		// Réinitialiser l'erreur quand l'utilisateur tape
		if (error) setError(null);
	};

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		setError(null);

		// Validation côté client
		if (formData.password !== formData.confirmPassword) {
			setError("Les mots de passe ne correspondent pas");
			return;
		}

		if (formData.password.length < 6) {
			setError("Le mot de passe doit contenir au moins 6 caractères");
			return;
		}

		setIsLoading(true);

		try {
			// Utiliser le bon endpoint pour l'inscription (useGetLogin fait l'inscription)
			const response = await fetch("http://back:82/user/signup", {
				method: "POST",
				headers: {
					"Content-Type": "application/json",
				},
				body: JSON.stringify({
					name: formData.lastName,
					mail: formData.email,
					password: formData.password,
				}),
			});

			const data = await response.json();

			if (response.ok) {
				console.log("Inscription réussie", data);
				onClose();
				// Vous pouvez soit rediriger vers la connexion, soit connecter automatiquement
				// onSwitchToLogin(); // Pour passer au formulaire de connexion
				// Ou connexion automatique si votre backend le permet
			} else {
				setError(data.error || "Erreur d'inscription");
			}
		} catch (error) {
			console.error("Erreur:", error);
			setError("Erreur de connexion au serveur");
		} finally {
			setIsLoading(false);
		}
	};

	return (
		<Modal isOpen={isOpen} onClose={onClose}>
			<div className="auth_form">
				<h2>Inscription</h2>
				<form onSubmit={handleSubmit}>
					{error && <div className="error_message">{error}</div>}
					<div className="form_row">
						<div className="form_group">
							<label htmlFor="lastName">Nom</label>
							<input
								type="text"
								id="lastName"
								name="lastName"
								value={formData.lastName}
								onChange={handleChange}
								required
								disabled={isLoading}
							/>
						</div>
					</div>
					<div className="form_group">
						<label htmlFor="email">Email</label>
						<input
							type="email"
							id="email"
							name="email"
							value={formData.email}
							onChange={handleChange}
							required
							disabled={isLoading}
						/>
					</div>
					<div className="form_group">
						<label htmlFor="password">Mot de passe</label>
						<input
							type="password"
							id="password"
							name="password"
							value={formData.password}
							onChange={handleChange}
							required
							minLength={6}
							disabled={isLoading}
						/>
					</div>
					<div className="form_group">
						<label htmlFor="confirmPassword">Confirmer le mot de passe</label>
						<input
							type="password"
							id="confirmPassword"
							name="confirmPassword"
							value={formData.confirmPassword}
							onChange={handleChange}
							required
							disabled={isLoading}
						/>
					</div>
					<button type="submit" className="btn_primary btn_full" disabled={isLoading}>
						{isLoading ? "Inscription..." : "S'inscrire"}
					</button>
				</form>
				<div className="auth_switch">
					<p>
						Déjà un compte ?{" "}
						<button type="button" className="link_button" onClick={onSwitchToLogin} disabled={isLoading}>
							Se connecter
						</button>
					</p>
				</div>
			</div>
		</Modal>
	);
}

// Composant pour le sélecteur de type de données
function DataTypeSelector() {
	const router = useRouter();
	const searchParams = useSearchParams();
	const currentType = searchParams.get("typeDataDisplay") || "reputation";
	const [currentTypeDataDisplay, setCurrentTypeDataDisplay] = useState(currentType);

	const { data: arianne, isLoading: isLoadingArianne } = useGetArianne({
		maille: searchParams.get("niveau") || "commune",
		code: searchParams.get("code") || "",
		isEnabled: searchParams.get("code") !== null,
	});

	console.log(arianne);

	useEffect(() => {
		const params = new URLSearchParams(searchParams.toString());
		params.set("typeDataDisplay", currentTypeDataDisplay);
		router.push(`?${params.toString()}`);
	}, [currentTypeDataDisplay, searchParams, router]);

	const handleTypeChange = (newType: string) => {
		// Créer une nouvelle URLSearchParams en préservant les autres paramètres
		setCurrentTypeDataDisplay(newType);
	};

	return (
		<div className="line_bar_filtre">
			<nav>
				{isLoadingArianne && <span>Chargement de la hiérarchie...</span>}
				{!isLoadingArianne && arianne?.length === 0 && <span>Aucune donnée disponible</span>}
				{arianne && arianne.length > 0 && <span>Fils d'arinnne : </span>}
				{arianne?.map((item, index) => (
					<span key={item.code}>
						{index > 0 && " > "}
						{index === 0 ? (
							<Link href={`?`}>France</Link>
						) : (
							<Link
								href={`?niveau=${item.niveau}&code=${item.code}&niveau_lower=${
									item.niveau === "region" ? "departement" : item.niveau === "departement" ? "commune" : ""
								}`}
							>
								{item.libelle}
							</Link>
						)}
					</span>
				))}
			</nav>
			<div className="data_type_selector">
				<label htmlFor="dataType" className="selector_label">
					Type de données :
				</label>
				<div className="selector_wrapper">
					{DATA_TYPE_OPTIONS.map((option) => (
						<button
							key={option.value}
							onClick={() => handleTypeChange(option.value)}
							className={`selector_button ${currentType === option.value ? "active" : ""}`}
						>
							{option.label}
						</button>
					))}
				</div>
			</div>
		</div>
	);
}

// CSS suggéré pour l'affichage des erreurs
const errorStyles = `
.error_message {
	background-color: #fee;
	color: #c33;
	padding: 10px;
	border-radius: 4px;
	margin-bottom: 15px;
	font-size: 14px;
	text-align: center;
}`;

// Composant Header
function Header() {
	const { openLogin, openRegister } = useAuth();

	return (
		<header className="header">
			<div className="header_container">
				<div className="header_logo">
					<h1>Mon App</h1>
				</div>
				<nav className="header_nav">
					<ul>
						<li>
							<a href="/">Accueil</a>
						</li>
						<li>
							<a href="/map">Carte</a>
						</li>
						<li>
							<a href="/contact">Contact</a>
						</li>
					</ul>
				</nav>

				<div className="header_actions">
					<button className="btn_secondary" onClick={openRegister}>
						S'inscrire
					</button>
					<button className="btn_primary" onClick={openLogin}>
						Connexion
					</button>
				</div>
			</div>
		</header>
	);
}

// Provider d'authentification
function AuthProvider({ children }: { children: React.ReactNode }) {
	const [isLoginOpen, setIsLoginOpen] = useState(false);
	const [isRegisterOpen, setIsRegisterOpen] = useState(false);

	const openLogin = () => {
		setIsLoginOpen(true);
		setIsRegisterOpen(false);
	};

	const openRegister = () => {
		setIsRegisterOpen(true);
		setIsLoginOpen(false);
	};

	const closeModals = () => {
		setIsLoginOpen(false);
		setIsRegisterOpen(false);
	};

	return (
		<AuthContext.Provider
			value={{
				openLogin,
				openRegister,
				closeModals,
				isLoginOpen,
				isRegisterOpen,
			}}
		>
			{children}
			<LoginModal isOpen={isLoginOpen} onClose={closeModals} onSwitchToRegister={openRegister} />
			<RegisterModal isOpen={isRegisterOpen} onClose={closeModals} onSwitchToLogin={openLogin} />
		</AuthContext.Provider>
	);
}

// Layout principal
export default function RootLayout({ children }: RootLayoutProps) {
	return (
		<AuthProvider>
			<div className="app_layout">
				<Header />
				<DataTypeSelector />
				<main className="main_content">{children}</main>
			</div>
		</AuthProvider>
	);
}
