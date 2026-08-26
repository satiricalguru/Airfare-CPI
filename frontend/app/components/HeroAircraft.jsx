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
    scene.background = new THREE.Color(0xffffff); // Pure Apple White Studio
    scene.fog = new THREE.Fog(0xffffff, 16, 36);

    const camera = new THREE.PerspectiveCamera(
      36,
      container.clientWidth / container.clientHeight,
      0.1,
      100
    );
    camera.position.set(0, 0.4, 7.8);

    // 2. High-Performance Renderer
    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: false,
      powerPreference: "high-performance",
    });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.25;
    container.appendChild(renderer.domElement);

    // 3. Apple Studio Lighting
    const hemiLight = new THREE.HemisphereLight(0xffffff, 0xe2e8f0, 2.0);
    hemiLight.position.set(0, 20, 0);
    scene.add(hemiLight);

    const keyLight = new THREE.DirectionalLight(0xffffff, 2.8);
    keyLight.position.set(7, 12, 8);
    keyLight.castShadow = true;
    keyLight.shadow.mapSize.width = 2048;
    keyLight.shadow.mapSize.height = 2048;
    keyLight.shadow.bias = -0.0001;
    scene.add(keyLight);

    const fillLight = new THREE.DirectionalLight(0xe0f2fe, 1.6);
    fillLight.position.set(-7, 6, 6);
    scene.add(fillLight);

    const blueRimLight = new THREE.DirectionalLight(0x0071e3, 2.4);
    blueRimLight.position.set(-8, 3, -6);
    scene.add(blueRimLight);

    const bottomBounce = new THREE.PointLight(0xf1f5f9, 1.6, 25);
    bottomBounce.position.set(0, -5, 0);
    scene.add(bottomBounce);

    // 4. Soft Contact Shadow Ground Plane
    const shadowGeo = new THREE.PlaneGeometry(24, 24);
    const shadowMat = new THREE.ShadowMaterial({ opacity: 0.08 });
    const groundShadow = new THREE.Mesh(shadowGeo, shadowMat);
    groundShadow.rotation.x = -Math.PI / 2;
    groundShadow.position.y = -1.7;
    groundShadow.receiveShadow = true;
    scene.add(groundShadow);

    // 5. Plane Container Group
    const airplaneFlightGroup = new THREE.Group();
    scene.add(airplaneFlightGroup);

    let planeModel = null;
    const rotatingFans = [];
    const interactiveMeshes = [];
    const originalMaterialsMap = new Map();

    // 6. Load Authentic Airbus A320 Commercial Jet Airliner via GLTFLoader
    const loader = new GLTFLoader();
    const modelUrl = "/models/airplane.glb";

    loader.load(
      modelUrl,
      (gltf) => {
        planeModel = gltf.scene;

        // Auto-center and normalize scale
        const box = new THREE.Box3().setFromObject(planeModel);
        const center = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3());
        const maxDim = Math.max(size.x, size.y, size.z);
        const targetScale = 5.2 / (maxDim || 1);

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
              let desc = "Passenger cabin monitoring 25 high-density DGCA city pairs";

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

    // Initial 3/4 Front Beauty Flight Angle (Nose pointing forward-left toward camera)
    airplaneFlightGroup.position.set(0, 0.1, 0);
    airplaneFlightGroup.rotation.set(0.12, -0.65, 0.08);

    // 7. Mouse & Raycasting Setup
    const raycaster = new THREE.Raycaster();
    const mouseVec = new THREE.Vector2(-100, -100);

    let targetRotX = 0.12;
    let targetRotY = -0.65;
    let targetRotZ = 0.08;
    let targetPosX = 0;
    let targetPosY = 0.1;

    let currentlyHovered = null;

    const onMouseMove = (e) => {
      const rect = container.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      const y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      mouseVec.x = x;
      mouseVec.y = y;
      setHudPos({ x: e.clientX - rect.left, y: e.clientY - rect.top });

      // Smooth flight banking and attitude response
      targetRotY = -0.65 + x * 0.65;
      targetRotX = 0.12 - y * 0.35;
      targetRotZ = 0.08 - x * 0.3;
      targetPosX = x * 0.45;
      targetPosY = 0.1 + y * 0.25;
    };

    window.addEventListener("mousemove", onMouseMove);

    // 8. Continuous Aerodynamic Flight Animation Loop
    let clock = new THREE.Clock();
    let animId;

    const highlightColor = new THREE.Color(0x0071e3); // Apple Electric Blue
    const highlightEmissive = new THREE.Color(0x0040aa); // Luminous Blue Glow

    const animate = () => {
      animId = requestAnimationFrame(animate);
      const elapsedTime = clock.getElapsedTime();

      // Continuous flight dynamics (turbulence, bank roll, pitch)
      const turbulence = Math.sin(elapsedTime * 1.5) * 0.05;
      const bankWobble = Math.cos(elapsedTime * 1.1) * 0.03;

      airplaneFlightGroup.rotation.x += (targetRotX + turbulence - airplaneFlightGroup.rotation.x) * 0.05;
      airplaneFlightGroup.rotation.y += (targetRotY - airplaneFlightGroup.rotation.y) * 0.05;
      airplaneFlightGroup.rotation.z += (targetRotZ + bankWobble - airplaneFlightGroup.rotation.z) * 0.05;
      airplaneFlightGroup.position.x += (targetPosX - airplaneFlightGroup.position.x) * 0.05;
      airplaneFlightGroup.position.y += (targetPosY + Math.sin(elapsedTime * 2.0) * 0.08 - airplaneFlightGroup.position.y) * 0.05;

      // Rotate jet engine turbine blades
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
            top: Math.min(Math.max(hudPos.y - 70, 16), 380),
            left: Math.min(Math.max(hudPos.x + 24, 16), 760),
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
