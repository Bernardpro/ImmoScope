import Form from "./form";
import StoreProvider from "./StoreProvider";

export default function Home() {
	return (
		<StoreProvider>
			{/* <Form /> */}
			<div className="flex justify-center items-center h-screen">
				<h1 className="text-4xl font-bold">Bienvenue sur l'application de gestion des zones</h1>
			</div>
		</StoreProvider>
	);
}
