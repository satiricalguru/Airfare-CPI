"use client";

import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";

export default function HeroAircraft() {
  const mountRef = useRef(null);
  const [hoveredPart, setHoveredPart] = useState(null);
  const [hudPos, setHudPos] = useState({ x: 0, y: 0 });
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    // 1. Scene & Camera Setup
    const scene = new THREE.Scene();
    scene.background = null; // Transparent to showcase clean background

    const camera = new THREE.PerspectiveCamera(
      36,
      container.clientWidth / container.clientHeight,
      0.1,
      100
    );
    // Camera positioned with optimal elevation to view the aircraft's full wingspan and cockpit
    camera.position.set(0, 0.4, 7.5);

    // 2. High-Performance WebGL Renderer with Alpha Support
    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
      powerPreference: "high-performance",
    });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.3;
    container.appendChild(renderer.domElement);

    // 3. Apple Studio Lighting
    const hemiLight = new THREE.HemisphereLight(0xffffff, 0xe2e8f0, 2.2);
    hemiLight.position.set(0, 20, 0);
    scene.add(hemiLight);

    const keyLight = new THREE.DirectionalLight(0xffffff, 2.8);
    keyLight.position.set(8, 14, 10);
    keyLight.castShadow = true;
    keyLight.shadow.mapSize.width = 2048;
    keyLight.shadow.mapSize.height = 2048;
    keyLight.shadow.bias = -0.0001;
    scene.add(keyLight);

    const fillLight = new THREE.DirectionalLight(0xe0f2fe, 1.8);
    fillLight.position.set(-8, 6, 8);
    scene.add(fillLight);

    const blueRimLight = new THREE.DirectionalLight(0x0071e3, 2.5);
    blueRimLight.position.set(0, 4, -8);
    scene.add(blueRimLight);

    const bottomBounce = new THREE.PointLight(0xf1f5f9, 1.8, 25);
    bottomBounce.position.set(0, -4, 2);
    scene.add(bottomBounce);

    // 4. Soft Contact Shadow Plane
    const shadowGeo = new THREE.PlaneGeometry(24, 24);
    const shadowMat = new THREE.ShadowMaterial({ opacity: 0.06 });
    const groundShadow = new THREE.Mesh(shadowGeo, shadowMat);
    groundShadow.rotation.x = -Math.PI / 2;
    groundShadow.position.y = -1.8;
    groundShadow.receiveShadow = true;
    scene.add(groundShadow);

    // 5. Plane Container Group
    const airplaneFlightGroup = new THREE.Group();
    scene.add(airplaneFlightGroup);

    let planeModel = null;
    const rotatingFans = [];
    const interactiveMeshes = [];
    const originalMaterialsMap = new Map();

    // 6. Load Airbus A320 Commercial Jet Airliner via GLTFLoader
    const loader = new GLTFLoader();
    const modelUrl = "/models/airplane.glb";

    loader.load(
      modelUrl,
      (gltf) => {
        planeModel = gltf.scene;

        // Auto-center and scale
        const box = new THREE.Box3().setFromObject(planeModel);
        const center = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3());
        const maxDim = Math.max(size.x, size.y, size.z);
        const targetScale = 5.0 / (maxDim || 1);

        planeModel.scale.set(targetScale, targetScale, targetScale);
        planeModel.position.set(
          -center.x * targetScale,
          -center.y * targetScale,
          -center.z * targetScale
        );

        // Traverse A320 parts & setup interactive shaders
        planeModel.traverse((child) => {
          if (child.isMesh) {
            child.castShadow = true;
            child.receiveShadow = true;
            interactiveMeshes.push(child);

            const nameLower = (child.name || "").toLowerCase();

            // Track turbine fan blades for rotation animation
            if (nameLower.includes("blade") || nameLower.includes("fanwheel") || nameLower.includes("cone")) {
              rotatingFans.push(child);
            }

            if (child.material) {
              child.material = child.material.clone();
              const origColor = child.material.color ? child.material.color.clone() : new THREE.Color(0xffffff);
              const origEmissive = child.material.emissive ? child.material.emissive.clone() : new THREE.Color(0x000000);

              originalMaterialsMap.set(child, {
                color: origColor,
                emissive: origEmissive,
                currentColor: origColor.clone(),
                targetColor: origColor.clone(),
                currentEmissive: origEmissive.clone(),
                targetEmissive: origEmissive.clone(),
              });

              // Intelligent part tagging for live telemetry HUD
              let partName = "Airbus A320 Commercial Fuselage";
              let desc = "Monitors 25 high-density DGCA city pairs across India";

              if (nameLower.includes("wing") || nameLower.includes("aileron") || nameLower.includes("flap") || nameLower.includes("slat") || nameLower.includes("wingtip")) {
                partName = "Supercritical Swept Wing";
                desc = "DGCA Passenger Volume Weighted (15.3M Pax/Month)";
              } else if (nameLower.includes("engine") || nameLower.includes("nacelle") || nameLower.includes("intake") || nameLower.includes("pylon") || nameLower.includes("blade") || nameLower.includes("fanwheel")) {
                partName = "CFM LEAP-1A Turbofan Propulsion";
                desc = "Jevons Geometric Micro-Index Computing Core";
              } else if (nameLower.includes("cockpit") || nameLower.includes("window") || nameLower.includes("nose")) {
                partName = "Fly-By-Wire Flight Deck & Avionics";
                desc = "Real-time automated price ingestion stream";
              } else if (nameLower.includes("vstab") || nameLower.includes("hstab") || nameLower.includes("rudder") || nameLower.includes("elevator")) {
                partName = "Empennage & Tail Stabilizer";
                desc = "MoSPI Headline CPI Dissemination Gateway";
              }

              child.userData = { partName, desc };
            }
          }
        });

        airplaneFlightGroup.add(planeModel);
        setIsLoaded(true);
      },
      undefined,
      (err) => console.error("Error loading A320 model:", err)
    );

    // Initial 3/4 Forward Beauty Flight Angle (Nose pointing forward towards the viewer with full wingspan visible)
    const baseRotY = Math.PI / 2 + 0.35; // Forward 3/4 angle
    const baseRotX = 0.08; // Level pitch
    const baseRotZ = 0.04; // Wings level

    airplaneFlightGroup.position.set(0, -0.15, 0);
    airplaneFlightGroup.rotation.set(baseRotX, baseRotY, baseRotZ);

    // 7. Mouse & Raycasting Setup
    const raycaster = new THREE.Raycaster();
    const mouseVec = new THREE.Vector2(-100, -100);

    let targetRotX = baseRotX;
    let targetRotY = baseRotY;
    let targetRotZ = baseRotZ;
    let targetPosX = 0;
    let targetPosY = -0.15;

    let currentlyHovered = null;

    const onMouseMove = (e) => {
      const rect = container.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      const y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      mouseVec.x = x;
      mouseVec.y = y;
      setHudPos({ x: e.clientX - rect.left, y: e.clientY - rect.top });

      // Subtle, smooth level flight steering with slight banking
      targetRotY = baseRotY + x * 0.35;
      targetRotX = baseRotX - y * 0.18;
      targetRotZ = baseRotZ - x * 0.15;
      targetPosX = x * 0.4;
      targetPosY = -0.15 + y * 0.25;
    };

    window.addEventListener("mousemove", onMouseMove);

    // 8. Continuous Flight Animation Loop
    let clock = new THREE.Clock();
    let animId;

    const highlightColor = new THREE.Color(0x0071e3); // Apple Electric Blue
    const highlightEmissive = new THREE.Color(0x0040aa); // Luminous Blue Glow

    const animate = () => {
      animId = requestAnimationFrame(animate);
      const elapsedTime = clock.getElapsedTime();

      // Continuous flight dynamics (turbulence, bank roll, altitude float)
      const turbulence = Math.sin(elapsedTime * 1.4) * 0.02;
      const altitudeFloat = Math.sin(elapsedTime * 1.8) * 0.05;

      airplaneFlightGroup.rotation.x += (targetRotX + turbulence - airplaneFlightGroup.rotation.x) * 0.05;
      airplaneFlightGroup.rotation.y += (targetRotY - airplaneFlightGroup.rotation.y) * 0.05;
      airplaneFlightGroup.rotation.z += (targetRotZ - airplaneFlightGroup.rotation.z) * 0.05;
      airplaneFlightGroup.position.x += (targetPosX - airplaneFlightGroup.position.x) * 0.05;
      airplaneFlightGroup.position.y += (targetPosY + altitudeFloat - airplaneFlightGroup.position.y) * 0.05;

      // Rotate turbofan turbine blades
      rotatingFans.forEach((fan) => {
        fan.rotation.y += 0.25;
      });

      // Raycast detection
      raycaster.setFromCamera(mouseVec, camera);
      const intersects = raycaster.intersectObjects(interactiveMeshes, true);

      if (intersects.length > 0) {
        const hit = intersects[0].object;
        if (currentlyHovered !== hit) {
          currentlyHovered = hit;
          setHoveredPart(hit.userData);
        }
      } else {
        if (currentlyHovered) {
          currentlyHovered = null;
          setHoveredPart(null);
        }
      }

      // Smooth slow color-transition animation for each mesh
      interactiveMeshes.forEach((mesh) => {
        const matState = originalMaterialsMap.get(mesh);
        if (!matState || !mesh.material) return;

        const isHit = currentlyHovered === mesh || (currentlyHovered && mesh.parent === currentlyHovered.parent && currentlyHovered.parent !== planeModel);

        if (isHit) {
          matState.targetColor.copy(highlightColor);
          matState.targetEmissive.copy(highlightEmissive);
        } else {
          matState.targetColor.copy(matState.color);
          matState.targetEmissive.copy(matState.emissive);
        }

        // Slow smooth lerp (0.07 per frame = silky luxury transition)
        if (mesh.material.color) {
          mesh.material.color.lerp(matState.targetColor, 0.07);
        }
        if (mesh.material.emissive) {
          mesh.material.emissive.lerp(matState.targetEmissive, 0.07);
        }
      });

      renderer.render(scene, camera);
    };

    animate();

    const onResize = () => {
      if (!container) return;
      camera.aspect = container.clientWidth / container.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(container.clientWidth, container.clientHeight);
    };

    window.addEventListener("resize", onResize);

    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("resize", onResize);
      cancelAnimationFrame(animId);
      if (renderer.domElement && container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
      renderer.dispose();
    };
  }, []);

  return (
    <div
      ref={mountRef}
      style={{
        width: "100%",
        height: "100%",
        cursor: "grab",
        position: "relative",
      }}
    >
      {/* Real-time Hover Telemetry Card */}
      {hoveredPart && (
        <div
          style={{
            position: "absolute",
            top: Math.min(Math.max(hudPos.y - 70, 20), 460),
            left: Math.min(Math.max(hudPos.x + 24, 20), 800),
            background: "rgba(255, 255, 255, 0.95)",
            backdropFilter: "blur(24px)",
            border: "1px solid rgba(0, 113, 227, 0.35)",
            borderRadius: 14,
            padding: "14px 20px",
            boxShadow: "0 12px 36px rgba(0, 0, 0, 0.08), 0 0 20px rgba(0, 113, 227, 0.15)",
            pointerEvents: "none",
            zIndex: 100,
            transition: "opacity 0.25s ease",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ width: 7, height: 7, borderRadius: "50%", background: "#0071e3", boxShadow: "0 0 8px #0071e3" }} />
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, fontWeight: 800, color: "#0071e3", textTransform: "uppercase", letterSpacing: "0.06em" }}>
              {hoveredPart.partName}
            </span>
          </div>
          <div style={{ fontSize: 13, color: "#1d1d1f", fontWeight: 600, marginTop: 4 }}>
            {hoveredPart.desc}
          </div>
          <div style={{ fontSize: 11, color: "#34c759", marginTop: 4, fontFamily: "var(--font-mono)", fontWeight: 700 }}>
            ● Active Ingestion Stream
          </div>
        </div>
      )}
    </div>
  );
}
