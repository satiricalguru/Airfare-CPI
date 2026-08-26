"use client";

import { useEffect, useState } from "react";

export default function CustomCursor() {
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
        target.closest("input") ||
        target.closest("[role='button']");
      setIsPointer(!!clickable);
    };

    const onMouseLeave = () => setIsVisible(false);

    window.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseleave", onMouseLeave);

    let animId;
    let currX = -100;
    let currY = -100;

    const loop = () => {
      animId = requestAnimationFrame(loop);
      currX += (mouseX - currX) * 0.2;
      currY += (mouseY - currY) * 0.2;
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
      {/* Apple Precision Dot */}
      <div
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          width: 7,
          height: 7,
          backgroundColor: "#0071e3",
          borderRadius: "50%",
          pointerEvents: "none",
          zIndex: 9999,
          transform: `translate3d(${pos.x - 3.5}px, ${pos.y - 3.5}px, 0)`,
          boxShadow: "0 0 10px rgba(0, 113, 227, 0.4)",
        }}
      />

      {/* Trailing Translucent Ring */}
      <div
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          width: isPointer ? 44 : 28,
          height: isPointer ? 44 : 28,
          border: isPointer ? "1.5px solid rgba(0, 113, 227, 0.6)" : "1px solid rgba(0, 0, 0, 0.15)",
          backgroundColor: isPointer ? "rgba(0, 113, 227, 0.05)" : "transparent",
          borderRadius: "50%",
          pointerEvents: "none",
          zIndex: 9998,
          transform: `translate3d(${trailingPos.x - (isPointer ? 22 : 14)}px, ${trailingPos.y - (isPointer ? 22 : 14)}px, 0)`,
          transition: "width 0.25s cubic-bezier(0.16, 1, 0.3, 1), height 0.25s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.2s ease",
        }}
      />
    </>
  );
}
