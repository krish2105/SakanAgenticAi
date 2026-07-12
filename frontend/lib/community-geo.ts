// Approximate community-center coordinates for Dubai, used to place comps on
// the map (individual markers are jittered slightly around the center since
// the synthetic dataset doesn't carry per-unit lat/lng).
export const COMMUNITY_COORDS: Record<string, [number, number]> = {
  "Business Bay": [25.1872, 55.2631],
  "Dubai Marina": [25.0805, 55.1403],
  "Jumeirah Village Circle": [25.0596, 55.2107],
  "Downtown Dubai": [25.1972, 55.2744],
  "Arabian Ranches": [25.0524, 55.2731],
  "DAMAC Hills": [25.0261, 55.2503],
  "Dubai South": [24.8965, 55.1614],
  "Mohammed Bin Rashid City": [25.1636, 55.2894],
  "Al Barari": [25.1042, 55.3232],
  "Jumeirah Lake Towers": [25.0693, 55.1417],
  "Palm Jumeirah": [25.1124, 55.1390],
  "Dubai Hills Estate": [25.1046, 55.2464],
  "Al Furjan": [25.0186, 55.1477],
  "Motor City": [25.0473, 55.2372],
  "Dubai Silicon Oasis": [25.1275, 55.3862],
};

export const DUBAI_CENTER: [number, number] = [25.1, 55.22];

function seededJitter(seed: string): [number, number] {
  let hash = 0;
  for (let i = 0; i < seed.length; i++) hash = (hash * 31 + seed.charCodeAt(i)) >>> 0;
  const jitterLat = ((hash % 1000) / 1000 - 0.5) * 0.02;
  const jitterLng = (((hash >> 10) % 1000) / 1000 - 0.5) * 0.02;
  return [jitterLat, jitterLng];
}

export function geoForComp(community: string, transactionId: string): [number, number] {
  const base = COMMUNITY_COORDS[community] ?? DUBAI_CENTER;
  const [dLat, dLng] = seededJitter(transactionId);
  return [base[0] + dLat, base[1] + dLng];
}
