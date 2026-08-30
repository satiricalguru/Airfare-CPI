"use client";

import { useState, useEffect, useRef, useSyncExternalStore } from "react";
import { INDIA_MAP_DATA } from "../data/indiaMapData";

// Geographically exact coordinates mapped inside viewBox="0 0 612 696" for all Indian States & UTs
const HUBS_CONFIG = [
  // Tier-1 National Hubs
  { code: "DEL", city: "New Delhi", state: "Delhi", x: 186.5, y: 210.0, pax: "1.20M", cpi: 106.0, trafficWeight: 1.0, zone: "North", labelPos: "top" },
  { code: "BOM", city: "Mumbai", state: "Maharashtra", x: 140.0, y: 434.0, pax: "870K", cpi: 107.4, trafficWeight: 0.95, zone: "West", labelPos: "left" },
  { code: "BLR", city: "Bengaluru", state: "Karnataka", x: 198.0, y: 562.0, pax: "950K", cpi: 107.5, trafficWeight: 0.92, zone: "South", labelPos: "bottom" },
  { code: "HYD", city: "Hyderabad", state: "Telangana", x: 236.0, y: 456.0, pax: "780K", cpi: 105.8, trafficWeight: 0.85, zone: "South", labelPos: "right" },
  { code: "CCU", city: "Kolkata", state: "West Bengal", x: 416.0, y: 348.0, pax: "740K", cpi: 108.2, trafficWeight: 0.80, zone: "East", labelPos: "right" },
  { code: "MAA", city: "Chennai", state: "Tamil Nadu", x: 246.0, y: 560.0, pax: "600K", cpi: 106.8, trafficWeight: 0.76, zone: "South", labelPos: "right" },

  // Key State Capitals & Major Commercial Centers
  { code: "AMD", city: "Ahmedabad", state: "Gujarat", x: 82.0, y: 342.0, pax: "370K", cpi: 106.2, trafficWeight: 0.65, zone: "West", labelPos: "left" },
  { code: "PNQ", city: "Pune", state: "Maharashtra", x: 156.0, y: 448.0, pax: "390K", cpi: 105.4, trafficWeight: 0.62, zone: "West", labelPos: "right" },
  { code: "GOI", city: "Goa", state: "Goa", x: 122.0, y: 512.0, pax: "450K", cpi: 109.1, trafficWeight: 0.68, zone: "West", labelPos: "left" },
  { code: "COK", city: "Kochi", state: "Kerala", x: 175.0, y: 615.0, pax: "430K", cpi: 104.5, trafficWeight: 0.60, zone: "South", labelPos: "left" },
  { code: "TRV", city: "Thiruvananthapuram", state: "Kerala", x: 188.0, y: 654.0, pax: "260K", cpi: 104.9, trafficWeight: 0.48, zone: "South", labelPos: "bottom" },
  { code: "JAI", city: "Jaipur", state: "Rajasthan", x: 146.0, y: 248.0, pax: "360K", cpi: 105.6, trafficWeight: 0.55, zone: "North", labelPos: "left" },
  { code: "LKO", city: "Lucknow", state: "Uttar Pradesh", x: 278.0, y: 254.0, pax: "380K", cpi: 106.4, trafficWeight: 0.58, zone: "North", labelPos: "top" },
  { code: "VNS", city: "Varanasi", state: "Uttar Pradesh", x: 326.0, y: 268.0, pax: "250K", cpi: 106.7, trafficWeight: 0.50, zone: "North", labelPos: "bottom" },
  { code: "PAT", city: "Patna", state: "Bihar", x: 366.0, y: 272.0, pax: "290K", cpi: 107.1, trafficWeight: 0.52, zone: "East", labelPos: "top" },
  { code: "BBI", city: "Bhubaneswar", state: "Odisha", x: 360.0, y: 418.0, pax: "310K", cpi: 105.9, trafficWeight: 0.54, zone: "East", labelPos: "right" },
  { code: "GAU", city: "Guwahati", state: "Assam", x: 486.0, y: 268.0, pax: "310K", cpi: 107.8, trafficWeight: 0.56, zone: "North-East", labelPos: "top" },
  { code: "SXR", city: "Srinagar", state: "Jammu and Kashmir", x: 168.0, y: 65.0, pax: "190K", cpi: 105.1, trafficWeight: 0.46, zone: "North", labelPos: "top" },
  { code: "IXC", city: "Chandigarh", state: "Chandigarh", x: 180.0, y: 160.0, pax: "240K", cpi: 104.8, trafficWeight: 0.48, zone: "North", labelPos: "top" },
  { code: "BHO", city: "Bhopal", state: "Madhya Pradesh", x: 202.0, y: 346.0, pax: "210K", cpi: 105.3, trafficWeight: 0.45, zone: "Central", labelPos: "left" },
  { code: "IDR", city: "Indore", state: "Madhya Pradesh", x: 162.0, y: 350.0, pax: "240K", cpi: 105.8, trafficWeight: 0.48, zone: "Central", labelPos: "left" },
  { code: "RPR", city: "Raipur", state: "Chhattisgarh", x: 290.0, y: 378.0, pax: "190K", cpi: 106.0, trafficWeight: 0.44, zone: "Central", labelPos: "right" },
  { code: "IXR", city: "Ranchi", state: "Jharkhand", x: 356.0, y: 334.0, pax: "220K", cpi: 105.7, trafficWeight: 0.46, zone: "East", labelPos: "right" },
  { code: "DED", city: "Dehradun", state: "Uttarakhand", x: 215.0, y: 172.0, pax: "170K", cpi: 106.8, trafficWeight: 0.42, zone: "North", labelPos: "top" },
  { code: "IXL", city: "Leh", state: "Ladakh", x: 212.0, y: 82.0, pax: "105K", cpi: 110.2, trafficWeight: 0.38, zone: "North", labelPos: "top" },
  { code: "IXB", city: "Bagdogra", state: "Sikkim", x: 422.0, y: 242.0, pax: "180K", cpi: 108.4, trafficWeight: 0.44, zone: "East", labelPos: "top" },
  { code: "VGA", city: "Vijayawada", state: "Andhra Pradesh", x: 272.0, y: 486.0, pax: "160K", cpi: 105.5, trafficWeight: 0.42, zone: "South", labelPos: "right" },
  { code: "VTZ", city: "Visakhapatnam", state: "Andhra Pradesh", x: 318.0, y: 462.0, pax: "220K", cpi: 106.3, trafficWeight: 0.46, zone: "South", labelPos: "right" },

  // North-Eastern & Island Lifelines
  { code: "IXA", city: "Agartala", state: "Tripura", x: 472.0, y: 336.0, pax: "130K", cpi: 106.5, trafficWeight: 0.36, zone: "North-East", labelPos: "bottom" },
  { code: "IMF", city: "Imphal", state: "Manipur", x: 536.0, y: 308.0, pax: "110K", cpi: 107.2, trafficWeight: 0.34, zone: "North-East", labelPos: "right" },
  { code: "AJL", city: "Aizawl", state: "Mizoram", x: 518.0, y: 348.0, pax: "80K", cpi: 108.1, trafficWeight: 0.30, zone: "North-East", labelPos: "right" },
  { code: "DMU", city: "Dimapur", state: "Nagaland", x: 540.0, y: 268.0, pax: "90K", cpi: 107.6, trafficWeight: 0.31, zone: "North-East", labelPos: "right" },
  { code: "SHL", city: "Shillong", state: "Meghalaya", x: 478.0, y: 292.0, pax: "75K", cpi: 107.0, trafficWeight: 0.28, zone: "North-East", labelPos: "bottom" },
  { code: "IXZ", city: "Port Blair", state: "Andaman and Nicobar Islands", x: 532.0, y: 590.0, pax: "140K", cpi: 111.4, trafficWeight: 0.40, zone: "Islands", labelPos: "left" },
];

const HUB_MAP = Object.fromEntries(HUBS_CONFIG.map((h) => [h.code, h]));

// Comprehensive Domestic Aviation Inter-State Network Graph
const ALL_NETWORK_ROUTES = [
  // High-Density Golden Trunk Corridors (High Velocity & Volume)
  { from: "DEL", to: "BOM", name: "Delhi ⇄ Mumbai", trafficWeight: 1.0, cpi: "106.0", fare: "₹6,240", change: "+3.2%", status: "Stable", desc: "Golden Corridor — 1.20M monthly passengers" },
  { from: "DEL", to: "BLR", name: "Delhi ⇄ Bengaluru", trafficWeight: 0.94, cpi: "107.5", fare: "₹6,850", change: "+2.9%", status: "Stable", desc: "Tech Corridor — 950K monthly passengers" },
  { from: "BOM", to: "BLR", name: "Mumbai ⇄ Bengaluru", trafficWeight: 0.88, cpi: "107.9", fare: "₹5,420", change: "+3.4%", status: "Surging", desc: "Commercial Shuttle — 780K monthly passengers" },
  { from: "DEL", to: "HYD", name: "Delhi ⇄ Hyderabad", trafficWeight: 0.86, cpi: "105.8", fare: "₹5,980", change: "+2.1%", status: "Stable", desc: "Deccan Trunk — 720K monthly passengers" },
  { from: "BOM", to: "HYD", name: "Mumbai ⇄ Hyderabad", trafficWeight: 0.82, cpi: "106.4", fare: "₹4,890", change: "+2.5%", status: "Stable", desc: "Western Gateway — 640K monthly passengers" },
  { from: "DEL", to: "CCU", name: "Delhi ⇄ Kolkata", trafficWeight: 0.84, cpi: "108.2", fare: "₹6,450", change: "+3.6%", status: "Surging", desc: "Eastern Express — 740K monthly passengers" },
  { from: "DEL", to: "MAA", name: "Delhi ⇄ Chennai", trafficWeight: 0.78, cpi: "106.8", fare: "₹6,620", change: "+2.4%", status: "Stable", desc: "Southern Trunk — 600K monthly passengers" },
  { from: "BLR", to: "MAA", name: "Bengaluru ⇄ Chennai", trafficWeight: 0.74, cpi: "104.2", fare: "₹3,450", change: "+1.2%", status: "Stable", desc: "Short-Haul Shuttle — 420K monthly passengers" },
  { from: "BOM", to: "GOI", name: "Mumbai ⇄ Goa", trafficWeight: 0.80, cpi: "109.1", fare: "₹4,980", change: "+4.8%", status: "Surging", desc: "Leisure Heavyweight — 450K monthly passengers" },
  { from: "BOM", to: "AMD", name: "Mumbai ⇄ Ahmedabad", trafficWeight: 0.72, cpi: "106.2", fare: "₹3,890", change: "+2.0%", status: "Stable", desc: "Industrial Corridor — 370K monthly passengers" },
  { from: "BLR", to: "COK", name: "Bengaluru ⇄ Kochi", trafficWeight: 0.68, cpi: "104.5", fare: "₹3,620", change: "+1.5%", status: "Stable", desc: "Southern Connector — 430K monthly passengers" },

  // State Capital Connectors & Regional Arteries
  { from: "DEL", to: "JAI", name: "Delhi ⇄ Jaipur", trafficWeight: 0.62, cpi: "105.6", fare: "₹3,150", change: "+1.8%", status: "Stable", desc: "North-West Connector" },
  { from: "DEL", to: "LKO", name: "Delhi ⇄ Lucknow", trafficWeight: 0.64, cpi: "106.4", fare: "₹3,820", change: "+2.2%", status: "Stable", desc: "UP Central Corridor" },
  { from: "DEL", to: "PAT", name: "Delhi ⇄ Patna", trafficWeight: 0.60, cpi: "107.1", fare: "₹5,240", change: "+3.1%", status: "Surging", desc: "Gangetic Plain Trunk" },
  { from: "DEL", to: "SXR", name: "Delhi ⇄ Srinagar", trafficWeight: 0.58, cpi: "105.1", fare: "₹5,860", change: "+2.7%", status: "Stable", desc: "Himalayan Corridor" },
  { from: "DEL", to: "IXC", name: "Delhi ⇄ Chandigarh", trafficWeight: 0.56, cpi: "104.8", fare: "₹2,950", change: "+1.1%", status: "Stable", desc: "Tri-City Shuttle" },
  { from: "DEL", to: "DED", name: "Delhi ⇄ Dehradun", trafficWeight: 0.50, cpi: "106.8", fare: "₹3,420", change: "+2.3%", status: "Stable", desc: "Uttarakhand Gateway" },
  { from: "DEL", to: "IXL", name: "Delhi ⇄ Leh", trafficWeight: 0.46, cpi: "110.2", fare: "₹7,850", change: "+5.2%", status: "Surging", desc: "High-Altitude Lifeline" },
  { from: "CCU", to: "GAU", name: "Kolkata ⇄ Guwahati", trafficWeight: 0.65, cpi: "107.8", fare: "₹4,680", change: "+3.0%", status: "Stable", desc: "North-East Gateway Hub" },
  { from: "CCU", to: "BBI", name: "Kolkata ⇄ Bhubaneswar", trafficWeight: 0.55, cpi: "105.9", fare: "₹3,250", change: "+1.6%", status: "Stable", desc: "Eastern Coastal Route" },
  { from: "CCU", to: "PAT", name: "Kolkata ⇄ Patna", trafficWeight: 0.54, cpi: "106.6", fare: "₹3,840", change: "+2.4%", status: "Stable", desc: "East Arterial" },
  { from: "CCU", to: "IXB", name: "Kolkata ⇄ Bagdogra", trafficWeight: 0.56, cpi: "108.4", fare: "₹4,120", change: "+3.8%", status: "Surging", desc: "Sikkim & Hills Link" },
  { from: "CCU", to: "IXZ", name: "Kolkata ⇄ Port Blair", trafficWeight: 0.52, cpi: "111.4", fare: "₹8,920", change: "+5.6%", status: "Surging", desc: "Bay of Bengal Lifeline" },
  { from: "MAA", to: "IXZ", name: "Chennai ⇄ Port Blair", trafficWeight: 0.50, cpi: "110.8", fare: "₹8,450", change: "+4.9%", status: "Surging", desc: "Island Strategic Link" },
  { from: "BOM", to: "IDR", name: "Mumbai ⇄ Indore", trafficWeight: 0.52, cpi: "105.8", fare: "₹3,750", change: "+1.9%", status: "Stable", desc: "Central MP Link" },
  { from: "BOM", to: "PNQ", name: "Mumbai ⇄ Pune", trafficWeight: 0.48, cpi: "105.4", fare: "₹2,680", change: "+1.0%", status: "Stable", desc: "Intra-State Feeder" },
  { from: "HYD", to: "VGA", name: "Hyderabad ⇄ Vijayawada", trafficWeight: 0.50, cpi: "105.5", fare: "₹3,180", change: "+1.4%", status: "Stable", desc: "Andhra Capital Link" },
  { from: "HYD", to: "VTZ", name: "Hyderabad ⇄ Visakhapatnam", trafficWeight: 0.54, cpi: "106.3", fare: "₹3,920", change: "+2.1%", status: "Stable", desc: "East Coast Tech Link" },
  { from: "HYD", to: "RPR", name: "Hyderabad ⇄ Raipur", trafficWeight: 0.46, cpi: "106.0", fare: "₹4,150", change: "+2.2%", status: "Stable", desc: "Chhattisgarh Link" },
  { from: "DEL", to: "BHO", name: "Delhi ⇄ Bhopal", trafficWeight: 0.52, cpi: "105.3", fare: "₹4,280", change: "+1.7%", status: "Stable", desc: "MP Capital Corridor" },
  { from: "DEL", to: "IXR", name: "Delhi ⇄ Ranchi", trafficWeight: 0.53, cpi: "105.7", fare: "₹4,890", change: "+2.3%", status: "Stable", desc: "Jharkhand Mineral Trunk" },
  { from: "DEL", to: "VNS", name: "Delhi ⇄ Varanasi", trafficWeight: 0.58, cpi: "106.7", fare: "₹4,360", change: "+2.6%", status: "Stable", desc: "Cultural Corridor" },
  { from: "COK", to: "TRV", name: "Kochi ⇄ Thiruvananthapuram", trafficWeight: 0.44, cpi: "104.9", fare: "₹2,480", change: "+0.9%", status: "Stable", desc: "Kerala Coastal Link" },

  // North-East Regional Feeder Grid
  { from: "GAU", to: "IXA", name: "Guwahati ⇄ Agartala", trafficWeight: 0.44, cpi: "106.5", fare: "₹2,840", change: "+1.9%", status: "Stable", desc: "Tripura Lifeline" },
  { from: "GAU", to: "IMF", name: "Guwahati ⇄ Imphal", trafficWeight: 0.42, cpi: "107.2", fare: "₹3,120", change: "+2.5%", status: "Stable", desc: "Manipur Connector" },
  { from: "GAU", to: "DMU", name: "Guwahati ⇄ Dimapur", trafficWeight: 0.38, cpi: "107.6", fare: "₹2,650", change: "+2.1%", status: "Stable", desc: "Nagaland Link" },
  { from: "GAU", to: "AJL", name: "Guwahati ⇄ Aizawl", trafficWeight: 0.36, cpi: "108.1", fare: "₹3,380", change: "+2.8%", status: "Stable", desc: "Mizoram Link" },
  { from: "GAU", to: "SHL", name: "Guwahati ⇄ Shillong", trafficWeight: 0.32, cpi: "107.0", fare: "₹1,980", change: "+1.2%", status: "Stable", desc: "Meghalaya Feeder" },
];

function subscribeToDocumentDark(callback) {
  if (typeof MutationObserver === "undefined") return () => {};
  const observer = new MutationObserver(callback);
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
  return () => observer.disconnect();
}

function getDocumentDarkSnapshot() {
  return typeof document !== "undefined" ? document.documentElement.classList.contains("dark") : false;
}

function getDocumentDarkServerSnapshot() {
  return false;
}

export default function IndiaNetworkMap({ isDarkMode: propDarkMode }) {
  const [selectedRoute, setSelectedRoute] = useState(ALL_NETWORK_ROUTES[0]);
  const [hoveredHub, setHoveredHub] = useState(null);
  const [hoveredState, setHoveredState] = useState(null);
  const domDarkMode = useSyncExternalStore(subscribeToDocumentDark, getDocumentDarkSnapshot, getDocumentDarkServerSnapshot);
  const isDarkMode = propDarkMode !== undefined ? propDarkMode : domDarkMode;
  const canvasRef = useRef(null);

  const activeFrom = selectedRoute?.from || "DEL";
  const activeTo = selectedRoute?.to || "BOM";
  const fromHub = HUB_MAP[activeFrom] || HUBS_CONFIG[0];
  const toHub = HUB_MAP[activeTo] || HUBS_CONFIG[1];

  // 60FPS Traffic-Proportional Particle Stream Animation on Canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

    let animId;
    const VB_WIDTH = 612;
    const VB_HEIGHT = 696;

    const setupCanvas = () => {
      const rect = canvas.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      ctx.scale(dpr, dpr);
    };

    setupCanvas();
    window.addEventListener("resize", setupCanvas);

    // Particle flight speed directly proportional to passenger traffic weight!
    const particles = ALL_NETWORK_ROUTES.map((route, i) => {
      const weight = route.trafficWeight || 0.5;
      // High-volume trunk routes travel significantly faster with larger pulses
      const baseSpeed = 0.0024 + weight * 0.0055;
      return {
        route,
        progress: (i * 0.08) % 1,
        speed: baseSpeed,
        weight,
        size: 1.8 + weight * 2.4,
      };
    });

    // Quadratic Bezier Helper
    const getBezierPoint = (p0, p1, p2, t) => {
      const invT = 1 - t;
      const x = invT * invT * p0.x + 2 * invT * t * p1.x + t * t * p2.x;
      const y = invT * invT * p0.y + 2 * invT * t * p1.y + t * t * p2.y;
      return { x, y };
    };

    const getControlPoint = (h1, h2) => {
      const dx = h2.x - h1.x;
      const dy = h2.y - h1.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      const curvature = Math.min(dist * 0.20, 42);
      const nx = -dy / dist;
      const ny = dx / dist;
      return {
        x: (h1.x + h2.x) / 2 + nx * curvature,
        y: (h1.y + h2.y) / 2 + ny * curvature,
      };
    };

    let time = 0;

    const render = () => {
      time += 0.016;
      const rect = canvas.getBoundingClientRect();
      const scaleX = rect.width / VB_WIDTH;
      const scaleY = rect.height / VB_HEIGHT;

      ctx.clearRect(0, 0, rect.width, rect.height);

      // 1. Draw Flight Stream Arcs
      ALL_NETWORK_ROUTES.forEach((r) => {
        const h1 = HUB_MAP[r.from];
        const h2 = HUB_MAP[r.to];
        if (!h1 || !h2) return;

        const isSelected =
          (r.from === activeFrom && r.to === activeTo) ||
          (r.from === activeTo && r.to === activeFrom);

        const cp = getControlPoint(h1, h2);

        ctx.beginPath();
        ctx.moveTo(h1.x * scaleX, h1.y * scaleY);
        ctx.quadraticCurveTo(cp.x * scaleX, cp.y * scaleY, h2.x * scaleX, h2.y * scaleY);

        if (isSelected) {
          // Luminous glowing active corridor (MoSPI Emerald)
          ctx.strokeStyle = isDarkMode ? "#9ac3a0" : "#3b6d4d";
          ctx.lineWidth = 3.4;
          ctx.shadowColor = isDarkMode ? "rgba(154, 195, 160, 0.75)" : "rgba(59, 109, 77, 0.45)";
          ctx.shadowBlur = 12;
          ctx.stroke();

          // Outer secondary soft glow
          ctx.beginPath();
          ctx.moveTo(h1.x * scaleX, h1.y * scaleY);
          ctx.quadraticCurveTo(cp.x * scaleX, cp.y * scaleY, h2.x * scaleX, h2.y * scaleY);
          ctx.strokeStyle = isDarkMode ? "rgba(154, 195, 160, 0.28)" : "rgba(59, 109, 77, 0.18)";
          ctx.lineWidth = 8;
          ctx.shadowBlur = 0;
          ctx.stroke();
        } else {
          // Subtle background route mesh with line opacity scaled by traffic
          const alpha = 0.12 + (r.trafficWeight || 0.4) * 0.16;
          ctx.strokeStyle = isDarkMode
            ? `rgba(185, 200, 186, ${alpha})`
            : `rgba(104, 119, 101, ${alpha + 0.05})`;
          ctx.lineWidth = 0.9 + (r.trafficWeight || 0.5) * 0.5;
          ctx.setLineDash([3, 3]);
          ctx.shadowBlur = 0;
          ctx.stroke();
          ctx.setLineDash([]);
        }
      });

      // 2. Animate Traffic-Speed Photon Particles
      particles.forEach((p) => {
        const h1 = HUB_MAP[p.route.from];
        const h2 = HUB_MAP[p.route.to];
        if (!h1 || !h2) return;

        const isSelected =
          (p.route.from === activeFrom && p.route.to === activeTo) ||
          (p.route.from === activeTo && p.route.to === activeFrom);

        // Progress advances according to route traffic volume
        p.progress += p.speed * (isSelected ? 1.4 : 1.0);
        if (p.progress > 1) p.progress = 0;

        const cp = getControlPoint(h1, h2);
        const pt = getBezierPoint(h1, cp, h2, p.progress);

        const screenX = pt.x * scaleX;
        const screenY = pt.y * scaleY;

        // Draw particle
        ctx.beginPath();
        ctx.arc(screenX, screenY, isSelected ? 4.5 : p.size, 0, Math.PI * 2);
        ctx.fillStyle = isSelected
          ? (isDarkMode ? "#ffffff" : "#3b6d4d")
          : (isDarkMode ? "#9ac3a0" : "#5a8864");
        ctx.shadowColor = isDarkMode ? "#9ac3a0" : "#3b6d4d";
        ctx.shadowBlur = isSelected ? 14 : 6;
        ctx.fill();
        ctx.shadowBlur = 0;
      });

      // 3. Expanding Radar Pulse on Selected Hubs
      [fromHub, toHub].forEach((hub, idx) => {
        if (!hub) return;
        const phase = (time * 1.6 + idx * 0.8) % 1;
        const radius = (8 + phase * 28) * ((scaleX + scaleY) / 2);
        const opacity = (1 - phase) * 0.6;

        ctx.beginPath();
        ctx.arc(hub.x * scaleX, hub.y * scaleY, radius, 0, Math.PI * 2);
        ctx.strokeStyle = isDarkMode ? `rgba(154, 195, 160, ${opacity})` : `rgba(59, 109, 77, ${opacity})`;
        ctx.lineWidth = 1.8;
        ctx.stroke();
      });

      animId = requestAnimationFrame(render);
    };

    animId = requestAnimationFrame(render);

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener("resize", setupCanvas);
    };
  }, [selectedRoute, activeFrom, activeTo, isDarkMode, fromHub, toHub]);

  return (
    <div
      className="stitch-card network-map-card"
      data-testid="india-network-map"
      style={{
        position: "relative",
        width: "100%",
        borderRadius: 16,
        overflow: "hidden",
        backgroundColor: "var(--paper-bright)",
        border: "1px solid var(--line)",
        boxShadow: isDarkMode ? "0 20px 50px rgba(0,0,0,0.35)" : "0 18px 50px rgba(31, 31, 24, 0.06)",
      }}
    >
      {/* Background Radar Grid Pattern */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage: isDarkMode
            ? "radial-gradient(circle at 50% 50%, rgba(154, 195, 160, 0.08) 1px, transparent 1px)"
            : "radial-gradient(circle at 50% 50%, rgba(59, 109, 77, 0.08) 1px, transparent 1px)",
          backgroundSize: "24px 24px",
          pointerEvents: "none",
        }}
      />

      {/* Main Centered Map Stage with Locked Aspect Ratio */}
      <div
        style={{
          position: "relative",
          width: "100%",
          maxWidth: 540,
          aspectRatio: "612 / 696",
          margin: "16px auto 12px",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {/* Unified Single SVG Map */}
        <svg
          viewBox={INDIA_MAP_DATA.viewBox}
          style={{
            position: "absolute",
            inset: 0,
            width: "100%",
            height: "100%",
            filter: isDarkMode ? "drop-shadow(0 4px 24px rgba(154, 195, 160, 0.1))" : "drop-shadow(0 4px 16px rgba(59, 109, 77, 0.08))",
          }}
        >
          {/* Layer 1: 36 Indian State Polygons */}
          <g id="india-states">
            {INDIA_MAP_DATA.locations.map((loc) => {
              const isHovered = hoveredState === loc.id;
              const hasActiveHub = (fromHub?.state === loc.name) || (toHub?.state === loc.name);

              let fillColor = isDarkMode ? "#1b241e" : "#f4f1e8";
              if (hasActiveHub) {
                fillColor = isDarkMode ? "rgba(154, 195, 160, 0.18)" : "rgba(59, 109, 77, 0.13)";
              } else if (isHovered) {
                fillColor = isDarkMode ? "rgba(154, 195, 160, 0.1)" : "rgba(59, 109, 77, 0.08)";
              }

              let strokeColor = isDarkMode ? "rgba(154, 195, 160, 0.28)" : "rgba(104, 119, 101, 0.62)";
              if (hasActiveHub) {
                strokeColor = isDarkMode ? "#9ac3a0" : "#3b6d4d";
              }

              return (
                <path
                  key={loc.id}
                  id={`state-${loc.id}`}
                  d={loc.path}
                  fill={fillColor}
                  stroke={strokeColor}
                  strokeWidth={hasActiveHub ? 1.6 : 0.8}
                  strokeLinejoin="round"
                  style={{
                    transition: "fill 0.25s ease, stroke 0.25s ease",
                    cursor: "pointer",
                  }}
                  data-testid={`india-map-state-${loc.id}`}
                  onMouseEnter={() => setHoveredState(loc.id)}
                  onMouseLeave={() => setHoveredState(null)}
                >
                  <title>{loc.name}</title>
                </path>
              );
            })}
          </g>

          {/* Layer 2: All State & UT Airport Hub Interactive Nodes */}
          <g id="airport-hubs">
            {HUBS_CONFIG.map((hub) => {
              const isOrigin = hub.code === activeFrom;
              const isDest = hub.code === activeTo;
              const isSelected = isOrigin || isDest;
              const isHovered = hoveredHub === hub.code;

              return (
                <g
                  key={hub.code}
                  transform={`translate(${hub.x}, ${hub.y})`}
                  style={{ cursor: "pointer" }}
                  data-testid={`india-map-hub-${hub.code.toLowerCase()}`}
                  onMouseEnter={() => setHoveredHub(hub.code)}
                  onMouseLeave={() => setHoveredHub(null)}
                  onClick={() => {
                    const matchingRoute = ALL_NETWORK_ROUTES.find((r) => r.from === hub.code || r.to === hub.code);
                    if (matchingRoute) setSelectedRoute(matchingRoute);
                  }}
                >
                  {/* Active Hub Radar Ring */}
                  {isSelected && (
                    <circle
                      r={13}
                      fill={isDarkMode ? "rgba(154, 195, 160, 0.16)" : "rgba(59, 109, 77, 0.12)"}
                      stroke={isDarkMode ? "#9ac3a0" : "#3b6d4d"}
                      strokeWidth={1.4}
                      strokeDasharray="3 3"
                    />
                  )}

                  {/* Hub Beacon Pin */}
                  <circle
                    r={isSelected ? 5.5 : (isHovered ? 4.5 : (hub.trafficWeight > 0.7 ? 3.5 : 2.6))}
                    fill={isSelected ? (isDarkMode ? "#9ac3a0" : "#3b6d4d") : (isDarkMode ? "#4a5d4e" : "#5d7362")}
                    stroke={isSelected ? "#ffffff" : (isDarkMode ? "#151b18" : "#ffffff")}
                    strokeWidth={isSelected ? 2 : 1.2}
                  />

                  {/* Hub IATA Label Pill */}
                  <g transform={`translate(${hub.labelPos === "left" ? -28 : (hub.labelPos === "right" ? 8 : -10)}, ${hub.labelPos === "top" ? -11 : 14})`}>
                    <rect
                      x={-2}
                      y={-10}
                      width={23}
                      height={13}
                      rx={3}
                      fill={isSelected ? (isDarkMode ? "#9ac3a0" : "#3b6d4d") : (isDarkMode ? "rgba(21, 27, 24, 0.92)" : "rgba(255, 253, 248, 0.94)")}
                      stroke={isSelected ? (isDarkMode ? "#9ac3a0" : "#3b6d4d") : (isDarkMode ? "rgba(154, 195, 160, 0.3)" : "rgba(59, 109, 77, 0.22)")}
                      strokeWidth={0.8}
                    />
                    <text
                      x={9.5}
                      y={-1}
                      textAnchor="middle"
                      fill={isSelected ? (isDarkMode ? "#151b18" : "#ffffff") : (isDarkMode ? "#f3f1e9" : "#172019")}
                      fontSize={8}
                      fontWeight={700}
                      fontFamily="var(--mono)"
                    >
                      {hub.code}
                    </text>
                  </g>
                </g>
              );
            })}
          </g>
        </svg>

        {/* Layer 3: 60FPS Flight Stream Canvas */}
        <canvas
          ref={canvasRef}
          style={{
            position: "absolute",
            inset: 0,
            width: "100%",
            height: "100%",
            pointerEvents: "none",
          }}
        />

        {/* Layer 4: Hover Hub Telemetry Tooltip */}
        {hoveredHub && HUB_MAP[hoveredHub] && (
          <div
            style={{
              position: "absolute",
              top: 16,
              right: 16,
              backgroundColor: "var(--paper-bright)",
              border: "1px solid var(--line)",
              borderRadius: 10,
              padding: "10px 14px",
              boxShadow: "0 10px 25px rgba(0,0,0,0.12)",
              pointerEvents: "none",
              zIndex: 10,
              backdropFilter: "blur(8px)",
              minWidth: 165,
            }}
          >
            <div style={{ fontWeight: 700, fontSize: 12.5, color: "var(--ink)", fontFamily: "var(--sans)", marginBottom: 2 }}>
              {HUB_MAP[hoveredHub].city} ({HUB_MAP[hoveredHub].code})
            </div>
            <div style={{ fontSize: 10.5, color: "var(--muted)", fontFamily: "var(--sans)", marginBottom: 6 }}>
              {HUB_MAP[hoveredHub].state} · {HUB_MAP[hoveredHub].zone} Zone
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10.5, fontFamily: "var(--sans)" }}>
              <span style={{ color: "var(--muted)" }}>Monthly Traffic:</span>
              <strong style={{ color: "var(--ink)", fontFamily: "var(--mono)" }}>{HUB_MAP[hoveredHub].pax} pax</strong>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10.5, fontFamily: "var(--sans)", marginTop: 2 }}>
              <span style={{ color: "var(--muted)" }}>DGCA Basket CPI:</span>
              <strong style={{ color: "var(--green)", fontFamily: "var(--mono)" }}>{HUB_MAP[hoveredHub].cpi}</strong>
            </div>
          </div>
        )}
      </div>

      {/* Interactive Bottom HUD Control Card - MoSPI Design Theme */}
      <div
        style={{
          margin: "0 14px 14px",
          padding: "14px 18px",
          borderRadius: 12,
          backgroundColor: "var(--paper-bright)",
          border: "1px solid var(--line)",
          boxShadow: isDarkMode ? "0 8px 30px rgba(0,0,0,0.4)" : "0 4px 16px rgba(31, 31, 24, 0.04)",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 14 }}>
          {/* Active Corridor Details */}
          <div>
            <div
              style={{
                fontSize: 9.5,
                fontWeight: 700,
                textTransform: "uppercase",
                letterSpacing: "0.1em",
                color: "var(--muted)",
                fontFamily: "var(--sans)",
                marginBottom: 2,
              }}
            >
              Active Aviation Corridor
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span
                style={{
                  fontSize: 20,
                  fontWeight: 800,
                  color: "var(--ink)",
                  fontFamily: "var(--sans)",
                  letterSpacing: "-0.02em",
                }}
              >
                {activeFrom} → {activeTo}
              </span>
              <span
                style={{
                  fontSize: 10,
                  fontWeight: 700,
                  letterSpacing: "0.04em",
                  textTransform: "uppercase",
                  padding: "2px 8px",
                  borderRadius: 999,
                  backgroundColor: selectedRoute?.status === "Surging" ? "rgba(200, 75, 49, 0.12)" : "var(--green-soft)",
                  color: selectedRoute?.status === "Surging" ? "var(--red, #c84b31)" : "var(--green)",
                  border: `1px solid ${selectedRoute?.status === "Surging" ? "rgba(200, 75, 49, 0.25)" : "rgba(59, 109, 77, 0.2)"}`,
                  fontFamily: "var(--sans)",
                }}
              >
                {selectedRoute?.status || "Stable"}
              </span>
            </div>
          </div>

          {/* Metric Stats */}
          <div style={{ display: "flex", alignItems: "center", gap: 22 }}>
            <div>
              <div
                style={{
                  fontSize: 9.5,
                  fontWeight: 700,
                  color: "var(--muted)",
                  textTransform: "uppercase",
                  letterSpacing: "0.08em",
                  fontFamily: "var(--sans)",
                }}
              >
                Jevons Index
              </div>
              <div
                style={{
                  fontSize: 20,
                  fontWeight: 600,
                  fontFamily: "var(--serif)",
                  color: "var(--ink)",
                }}
              >
                {selectedRoute?.cpi || "106.0"}
              </div>
            </div>
            <div>
              <div
                style={{
                  fontSize: 9.5,
                  fontWeight: 700,
                  color: "var(--muted)",
                  textTransform: "uppercase",
                  letterSpacing: "0.08em",
                  fontFamily: "var(--sans)",
                }}
              >
                Average Fare
              </div>
              <div
                style={{
                  fontSize: 20,
                  fontWeight: 600,
                  fontFamily: "var(--serif)",
                  color: "var(--ink)",
                }}
              >
                {selectedRoute?.fare || "₹6,240"}
              </div>
            </div>
            <div>
              <div
                style={{
                  fontSize: 9.5,
                  fontWeight: 700,
                  color: "var(--muted)",
                  textTransform: "uppercase",
                  letterSpacing: "0.08em",
                  fontFamily: "var(--sans)",
                }}
              >
                MoM Movement
              </div>
              <div
                style={{
                  fontSize: 18,
                  fontWeight: 700,
                  fontFamily: "var(--sans)",
                  color: "var(--green)",
                }}
              >
                {selectedRoute?.change || "+3.2%"}
              </div>
            </div>
          </div>
        </div>

        {/* Quick Corridor Selector Pills */}
        <div style={{ display: "flex", gap: 6, marginTop: 12, overflowX: "auto", paddingBottom: 2 }}>
          {ALL_NETWORK_ROUTES.slice(0, 8).map((r) => {
            const isCurrent = r.from === activeFrom && r.to === activeTo;
            return (
              <button
                key={`${r.from}-${r.to}`}
                onClick={() => setSelectedRoute(r)}
                data-testid={`india-map-route-${r.from.toLowerCase()}-${r.to.toLowerCase()}-button`}
                style={{
                  padding: "5px 11px",
                  borderRadius: 6,
                  fontSize: 11,
                  fontWeight: 600,
                  fontFamily: "var(--mono)",
                  cursor: "pointer",
                  whiteSpace: "nowrap",
                  backgroundColor: isCurrent ? "var(--green)" : "var(--surface-subtle, rgba(0, 0, 0, 0.025))",
                  color: isCurrent ? "#ffffff" : "var(--ink)",
                  border: isCurrent ? "1px solid var(--green)" : "1px solid var(--line)",
                  transition: "all 0.15s ease",
                }}
              >
                {r.from} ⇄ {r.to}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
