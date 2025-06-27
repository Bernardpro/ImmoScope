interface Equipment {
	nomrs: string;
	cnomrs: string;
	libelle_commune: string;
	code_commune: string;
	dom: string;
	sdom: string;
	typequ: string;
	siret: string;
	lambert_x: string | null;
	lambert_y: string | null;
	longitude: string | null;
	latitude: string | null;
	qualite_xy: string;
	epsg: string;
	qualite_geoloc: string;
	tr_dist_precision: string;
	lib_mod: string;
}

export interface EquipmentData {
	data: Equipment[];
}
