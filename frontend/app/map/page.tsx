"use client";

import React, { useState } from "react";
import Map from "./Map";
import SidebarLeft from "./SidebarLeft";
import SidebarRight from "./SideBarRight";
import "./page.scss";
import { useSearchMailles } from "@/api/maillage";
import { useSearchParams } from "next/navigation";

export default function Page() {
	const searchParams = useSearchParams();

	const code_selecting = searchParams.get("code_selecting");
	const [isSidebarOpen, setIsSidebarOpen] = useState(true);

	const toggleSidebar = () => {
		setIsSidebarOpen((prev) => !prev);
	};

	// Callbacks personnalisés pour les actions de la sidebar
	const handleApplyFilters = (location: string) => {
		console.log("Filtres appliqués depuis la page principale:", location);
		// Ici vous pouvez ajouter votre logique métier spécifique
	};

	const handleReset = () => {
		console.log("Reset depuis la page principale");
		// Logique spécifique au reset si nécessaire
	};

	return (
		<div className="map_page">
			<main className="map_main">
				{/* Sidebar gauche avec le nouveau composant */}
				<SidebarLeft
					isOpen={isSidebarOpen}
					onToggle={toggleSidebar}
					onApplyFilters={handleApplyFilters}
					onReset={handleReset}
					useSearchMailles={useSearchMailles}
				>
					{/* Contenu personnalisé à ajouter dans la sidebar */}
					<div className="filter_section"></div>
				</SidebarLeft>

				{/* Zone de la carte */}
				<div className="map_container">
					<Map />
				</div>

				{/* Sidebar right to display chart */}
				{code_selecting !== null && <SidebarRight code_selecting={code_selecting} />}
			</main>
		</div>
	);
}
