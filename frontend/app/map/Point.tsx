import L, { LatLngExpression } from "leaflet";
import { useEffect, useState } from "react";
import { LayerGroup, Marker, Popup } from "react-leaflet";

const Point = ({ entity }) => {
	const [coord, setCoord] = useState<LatLngExpression>([0, 0]);

	useEffect(() => {
		if (!entity.position) return;

		const lat = parseFloat(entity.position.split(",")[0]);
		const long = parseFloat(entity.position.split(",")[1]);

		setCoord([lat, long]);
	}, [entity]);
	return (
		<LayerGroup>
			<Marker position={coord} icon={schoolIcon}>
				<Popup>Place</Popup>
			</Marker>
		</LayerGroup>
	);
};

export default Point;
