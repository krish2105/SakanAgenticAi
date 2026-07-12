"use client";

import { useMemo } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { geoForComp, DUBAI_CENTER } from "@/lib/community-geo";
import type { Comp } from "@/lib/types";

export function CompsMap({
  comps,
  selectedId,
  onSelect,
}: {
  comps: Comp[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const points = useMemo(
    () => comps.map((c) => ({ comp: c, position: geoForComp(c.community, c.transaction_id) })),
    [comps]
  );

  return (
    <MapContainer
      center={DUBAI_CENTER}
      zoom={11}
      scrollWheelZoom
      className="h-full w-full rounded-xl"
      style={{ background: "rgb(var(--surface))" }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {points.map(({ comp, position }) => {
        const active = comp.transaction_id === selectedId;
        return (
          <CircleMarker
            key={comp.transaction_id}
            center={position}
            radius={active ? 9 : 6}
            pathOptions={{
              color: active ? "#C9A227" : "#8A94AC",
              fillColor: active ? "#C9A227" : "#25324A",
              fillOpacity: 0.85,
              weight: active ? 2 : 1,
            }}
            eventHandlers={{ click: () => onSelect(comp.transaction_id) }}
          >
            <Popup>
              <div className="font-sans text-xs">
                <div className="font-semibold">{comp.building}</div>
                <div>
                  {comp.bedrooms}BR {comp.property_type} · {comp.community}
                </div>
                <div>AED {comp.price?.toLocaleString()}</div>
              </div>
            </Popup>
          </CircleMarker>
        );
      })}
    </MapContainer>
  );
}
