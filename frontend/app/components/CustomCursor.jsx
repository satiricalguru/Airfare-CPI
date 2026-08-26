"use client";

import { useEffect, useState } from "react";

export default function CustomCursor({ isAircraftHovered }) {
  const [pos, setPos] = useState({ x: -100, y: -100 });
  const [trailingPos, setTrailingPos] = useState({ x: -100, y: -100 });
  const [isPointer, setIsPointer] = useState(false);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    let mouseX = -100;
    let mouseY = -100;

    const onMouseMove = (e) => {
      mouseX = e.clientX;
      mouseY = e.clientY;
      setPos({ x: mouseX, y: mouseY });
      if (!isVisible) setIsVisible(true);

      const target = e.target;
      const clickable =
        target.closest("button") ||
        target.closest("a") ||
        target.closest("[role='button']") ||
        target.classList.contains("clickable");
      setIsPointer(!!clickable);
    };

    const onMouseLeave = () => setIsVisible(false);

    window.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseleave", onMouseLeave);

    // Smooth trailing physics
    let animId;
    let currX = -100;
    let currY = -100;

    const loop = () => {
      animId = requestAnimationFrame(loop);
      currX += (mouseX - currX) * 0.15;
      currY += (mouseY - currY) * 0.15;
      setTrailingPos({ x: currX, y: currY });
    };

    loop();

    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseleave", onMouseLeave);
      cancelAnimationFrame(animId);
    };
  }, [isVisible]);

  if (!isVisible) return null;

  return (
    <>
      {/* Small Precision Dot */}
      <div
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          width: 8,
          height: 8,
          backgroundColor: isAircraftHovered ? "#f9bd22" : "#00f0ff",
          borderRadius: "50%",
          pointerEvents: "none",
          zIndex: 9999,
          transform: `translate3d(${pos.x - 4}px, ${pos.y - 4}px, 0)`,
          boxShadow: isAircraftHovered
            ? "0 0 12px #f9bd22, 0 0 20px #f9bd22"
            : "0 0 10px #00f0ff, 0 0 18px #00f0ff",
          transition: "background-color 0.2s ease",
        }}
      />

      {/* Trailing Aura Ring */}
      <div
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          width: isAircraftHovered ? 84 : isPointer ? 44 : 32,
          height: isAircraftHovered ? 84 : isPointer ? 44 : 32,
          border: isAircraftHovered
            ? "1.5px solid rgba(249, 189, 34, 0.85)"
            : isPointer
            ? "1.5px solid rgba(76, 215, 246, 0.8)"
            : "1px solid rgba(76, 215, 246, 0.4)",
          backgroundColor: isAircraftHovered
            ? "rgba(249, 189, 34, 0.1)"
            : isPointer
            ? "rgba(6, 182, 212, 0.08)"
            : "transparent",
          borderRadius: "50%",
          pointerEvents: "none",
          zIndex: 9998,
          transform: `translate3d(${trailingPos.x - (isAircraftHovered ? 42 : isPointer ? 22 : 16)}px, ${
            trailingPos.y - (isAircraftHovered ? 42 : isPointer ? 22 : 16)
          }px, 0)`,
          transition: "width 0.25s cubic-bezier(0.16, 1, 0.3, 1), height 0.25s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.2s ease, background-color 0.2s ease",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          backdropFilter: isAircraftHovered ? "blur(4px)" : "none",
        }}
      >
        {isAircraftHovered && (
          <span
            style={{
              fontFamily: "var(--font-mono, 'JetBrains Mono', monospace)",
              fontSize: 10,
              fontWeight: 700,
              color: "#f9bd22",
              letterSpacing: "0.15em",
              textTransform: "uppercase",
            }}
          >
            EXPLORE
          </span>
        )}
      </div>
    </>
  );
}
