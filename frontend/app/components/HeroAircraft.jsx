"use client";

import { useEffect, useRef, useState } from "react";
import * as THREE from "three";

export default function HeroAircraft() {
  const mountRef = useRef(null);
  const [hoveredPart, setHoveredPart] = useState(null);
  const [hudPos, setHudPos] = useState({ x: 0, y: 0 });

  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    // 1. Scene & Camera
    const scene = new THREE.Scene();
    // Pure clean Apple white studio background
    scene.background = new THREE.Color(0xffffff);
    scene.fog = new THREE.Fog(0xffffff, 12, 28);

    const camera = new THREE.PerspectiveCamera(
      42,
      container.clientWidth / container.clientHeight,
      0.1,
      100
    );
    camera.position.set(0, 1.2, 8.5);

    // 2. Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: "high-performance" });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.15;
    container.appendChild(renderer.domElement);

    // 3. Apple Studio Lighting
    const hemiLight = new THREE.HemisphereLight(0xffffff, 0xe2e8f0, 1.4);
    hemiLight.position.set(0, 20, 0);
    scene.add(hemiLight);

    const keyLight = new THREE.DirectionalLight(0xffffff, 2.4);
    keyLight.position.set(6, 12, 8);
    keyLight.castShadow = true;
    keyLight.shadow.mapSize.width = 2048;
    keyLight.shadow.mapSize.height = 2048;
    keyLight.shadow.bias = -0.0001;
    scene.add(keyLight);

    const blueRimLight = new THREE.DirectionalLight(0x0071e3, 1.8);
    blueRimLight.position.set(-8, 4, -6);
    scene.add(blueRimLight);

    const warmBounceLight = new THREE.PointLight(0xfff7ed, 1.2, 20);
    warmBounceLight.position.set(0, -4, 2);
    scene.add(warmBounceLight);

    // 4. Soft Ground Shadow Plane
    const shadowGeo = new THREE.PlaneGeometry(30, 30);
    const shadowMat = new THREE.ShadowMaterial({ opacity: 0.08 });
    const groundShadow = new THREE.Mesh(shadowGeo, shadowMat);
    groundShadow.rotation.x = -Math.PI / 2;
    groundShadow.position.y = -2.2;
    groundShadow.receiveShadow = true;
    scene.add(groundShadow);

    // 5. Realistic Commercial Aircraft Hierarchy
    const airplaneGroup = new THREE.Group();
    scene.add(airplaneGroup);

    // Interactive Mesh Registry
    const interactiveMeshes = [];

    // Shared Base Materials (Apple Pristine Pearlescent White & Metallic Alloys)
    const createAircraftMaterial = (name, baseColor = 0xf8fafc, metalness = 0.4, roughness = 0.25) => {
      const mat = new THREE.MeshPhysicalMaterial({
        color: baseColor,
        metalness: metalness,
        roughness: roughness,
        clearcoat: 0.8,
        clearcoatRoughness: 0.15,
        reflectivity: 0.8,
      });
      mat.userData = { originalColor: new THREE.Color(baseColor), name };
      return mat;
    };

    const liveryBlueMaterial = new THREE.MeshStandardMaterial({
      color: 0x0071e3,
      metalness: 0.6,
      roughness: 0.2,
    });

    const glassMaterial = new THREE.MeshPhysicalMaterial({
      color: 0x111827,
      metalness: 0.9,
      roughness: 0.05,
      transmission: 0.3,
      reflectivity: 1.0,
      clearcoat: 1.0,
    });

    const chromeMaterial = new THREE.MeshStandardMaterial({
      color: 0xcfd8dc,
      metalness: 0.95,
      roughness: 0.1,
    });

    // ── FUSELAGE ──
    const fuselageMat = createAircraftMaterial("Fuselage (Airframe Body)", 0xffffff, 0.2, 0.2);
    // Smooth aerodynamic fuselage using Spline Extrusion / Lathe
    const fuselagePoints = [];
    fuselagePoints.push(new THREE.Vector2(0, 2.6)); // Nose tip
    fuselagePoints.push(new THREE.Vector2(0.22, 2.4));
    fuselagePoints.push(new THREE.Vector2(0.48, 2.0));
    fuselagePoints.push(new THREE.Vector2(0.55, 1.4));
    fuselagePoints.push(new THREE.Vector2(0.55, -1.8)); // Main cabin
    fuselagePoints.push(new THREE.Vector2(0.48, -2.4));
    fuselagePoints.push(new THREE.Vector2(0.24, -3.0));
    fuselagePoints.push(new THREE.Vector2(0.04, -3.4)); // Tail cone
    fuselagePoints.push(new THREE.Vector2(0, -3.45));

    const fuselageGeo = new THREE.LatheGeometry(fuselagePoints, 48);
    const fuselageMesh = new THREE.Mesh(fuselageGeo, fuselageMat);
    fuselageMesh.castShadow = true;
    fuselageMesh.receiveShadow = true;
    fuselageMesh.rotation.x = Math.PI / 2;
    fuselageMesh.userData = { partName: "Fuselage & Main Passenger Cabin", desc: "Monitors 25 high-density DGCA city pairs across India" };
    airplaneGroup.add(fuselageMesh);
    interactiveMeshes.push(fuselageMesh);

    // ── COCKPIT WINDSHIELD ──
    const cockpitGeo = new THREE.SphereGeometry(0.38, 32, 16, 0, Math.PI * 2, 0, Math.PI * 0.5);
    cockpitGeo.scale(0.7, 0.35, 1.4);
    const cockpitMesh = new THREE.Mesh(cockpitGeo, glassMaterial);
    cockpitMesh.position.set(0, 0.34, 1.35);
    cockpitMesh.rotation.x = -0.15;
    cockpitMesh.userData = { partName: "Cockpit Avionics & Telemetry", desc: "Real-time automated price ingestion engine" };
    airplaneGroup.add(cockpitMesh);
    interactiveMeshes.push(cockpitMesh);

    // ── WINGS (Swept Supercritical Aerofoil with Dihedral) ──
    const wingMat = createAircraftMaterial("Supercritical Wings", 0xf1f5f9, 0.3, 0.2);

    const wingShape = new THREE.Shape();
    wingShape.moveTo(0, 0.6);
    wingShape.lineTo(4.4, -2.4); // Swept wing tip
    wingShape.lineTo(4.2, -2.9);
    wingShape.lineTo(0, -1.4);
    wingShape.closePath();

    const wingExtrude = { depth: 0.08, bevelEnabled: true, bevelSegments: 3, steps: 1, bevelSize: 0.03, bevelThickness: 0.03 };
    const wingGeo = new THREE.ExtrudeGeometry(wingShape, wingExtrude);

    // Right Wing
    const rightWing = new THREE.Mesh(wingGeo, wingMat);
    rightWing.position.set(0, -0.05, 0.1);
    rightWing.rotation.x = Math.PI / 2;
    rightWing.rotation.y = 0.06; // Dihedral angle
    rightWing.castShadow = true;
    rightWing.receiveShadow = true;
    rightWing.userData = { partName: "High-Lift Supercritical Wing", desc: "Represents DGCA passenger volume weighting (15.3M Pax/mo)" };
    airplaneGroup.add(rightWing);
    interactiveMeshes.push(rightWing);

    // Left Wing
    const leftWing = rightWing.clone();
    leftWing.scale.x = -1;
    leftWing.position.set(0, -0.05, 0.1);
    leftWing.rotation.y = -0.06;
    leftWing.castShadow = true;
    leftWing.receiveShadow = true;
    leftWing.userData = { partName: "High-Lift Supercritical Wing", desc: "Represents DGCA passenger volume weighting (15.3M Pax/mo)" };
    airplaneGroup.add(leftWing);
    interactiveMeshes.push(leftWing);

    // Blended Winglets (Upward Angled)
    const wingletGeo = new THREE.BoxGeometry(0.06, 0.5, 0.6);
    const rightWinglet = new THREE.Mesh(wingletGeo, liveryBlueMaterial);
    rightWinglet.position.set(4.35, 0.22, -2.55);
    rightWinglet.rotation.z = -0.3;
    airplaneGroup.add(rightWinglet);

    const leftWinglet = rightWinglet.clone();
    leftWinglet.position.x = -4.35;
    leftWinglet.rotation.z = 0.3;
    airplaneGroup.add(leftWinglet);

    // ── HIGH-BYPASS TURBOFAN ENGINES ──
    const engineMat = createAircraftMaterial("Turbofan Jet Engines", 0xe2e8f0, 0.7, 0.15);
    const engineNacelleGeo = new THREE.CylinderGeometry(0.36, 0.42, 1.8, 32);
    
    // Right Engine
    const rightEngine = new THREE.Mesh(engineNacelleGeo, engineMat);
    rightEngine.position.set(1.4, -0.38, -0.4);
    rightEngine.rotation.x = Math.PI / 2;
    rightEngine.castShadow = true;
    rightEngine.userData = { partName: "High-Bypass Turbofan Engine", desc: "Jevons Geometric Micro-Index Computing Core" };
    airplaneGroup.add(rightEngine);
    interactiveMeshes.push(rightEngine);

    // Engine Chrome Intake Ring
    const intakeRingGeo = new THREE.TorusGeometry(0.38, 0.04, 16, 32);
    const rightIntake = new THREE.Mesh(intakeRingGeo, chromeMaterial);
    rightIntake.position.set(1.4, -0.38, 0.5);
    airplaneGroup.add(rightIntake);

    // Engine Fan Spinner
    const spinnerGeo = new THREE.ConeGeometry(0.12, 0.3, 16);
    const rightSpinner = new THREE.Mesh(spinnerGeo, chromeMaterial);
    rightSpinner.position.set(1.4, -0.38, 0.45);
    rightSpinner.rotation.x = Math.PI / 2;
    airplaneGroup.add(rightSpinner);

    // Left Engine
    const leftEngine = rightEngine.clone();
    leftEngine.position.x = -1.4;
    leftEngine.userData = { partName: "High-Bypass Turbofan Engine", desc: "Jevons Geometric Micro-Index Computing Core" };
    airplaneGroup.add(leftEngine);
    interactiveMeshes.push(leftEngine);

    const leftIntake = rightIntake.clone();
    leftIntake.position.x = -1.4;
    leftIntake.position.y = -0.38;
    leftIntake.position.z = 0.5;
    airplaneGroup.add(leftIntake);

    const leftSpinner = rightSpinner.clone();
    leftSpinner.position.x = -1.4;
    airplaneGroup.add(leftSpinner);

    // ── TAIL SECTION (Vertical Fin & Stabilizers) ──
    const tailFinShape = new THREE.Shape();
    tailFinShape.moveTo(0, 0);
    tailFinShape.lineTo(0.04, 1.8);
    tailFinShape.lineTo(0.8, 1.8);
    tailFinShape.lineTo(1.6, 0);
    tailFinShape.closePath();

    const tailFinGeo = new THREE.ExtrudeGeometry(tailFinShape, { depth: 0.06, bevelEnabled: true, bevelSegments: 2, bevelSize: 0.02, bevelThickness: 0.02 });
    const tailFin = new THREE.Mesh(tailFinGeo, liveryBlueMaterial);
    tailFin.position.set(-0.03, 0.35, -1.8);
    tailFin.rotation.y = -Math.PI / 2;
    tailFin.castShadow = true;
    tailFin.userData = { partName: "Vertical Stabilizer & Fin", desc: "MoSPI National CPI Dissemination Gateway" };
    airplaneGroup.add(tailFin);
    interactiveMeshes.push(tailFin);

    // Horizontal Stabilizers
    const horizStabShape = new THREE.Shape();
    horizStabShape.moveTo(0, 0);
    horizStabShape.lineTo(1.6, -1.0);
    horizStabShape.lineTo(1.4, -1.3);
    horizStabShape.lineTo(0, -0.6);
    horizStabShape.closePath();
    const horizStabGeo = new THREE.ExtrudeGeometry(horizStabShape, { depth: 0.04, bevelEnabled: true, bevelSegments: 2, bevelSize: 0.01, bevelThickness: 0.01 });

    const rightStab = new THREE.Mesh(horizStabGeo, wingMat);
    rightStab.position.set(0, 0.15, -2.6);
    rightStab.rotation.x = Math.PI / 2;
    airplaneGroup.add(rightStab);

    const leftStab = rightStab.clone();
    leftStab.scale.x = -1;
    airplaneGroup.add(leftStab);

    // Set initial pose
    airplaneGroup.position.set(0, 0.2, 0);
    airplaneGroup.rotation.set(-0.12, 0.45, 0.08);

    // 6. Dynamic Raycasting on Mouse Move
    const raycaster = new THREE.Raycaster();
    const mouseVec = new THREE.Vector2(-100, -100);

    let targetRotX = -0.12;
    let targetRotY = 0.45;
    let targetRotZ = 0.08;
    let targetPosX = 0;
    let targetPosY = 0.2;

    let currentHoveredMesh = null;

    const onMouseMove = (e) => {
      const rect = container.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      const y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      mouseVec.x = x;
      mouseVec.y = y;

      setHudPos({ x: e.clientX - rect.left, y: e.clientY - rect.top });

      // Spring flight response
      targetRotY = 0.45 + x * 0.75;
      targetRotX = -0.12 - y * 0.45;
      targetRotZ = 0.08 - x * 0.35;
      targetPosX = x * 0.5;
      targetPosY = 0.2 + y * 0.3;
    };

    window.addEventListener("mousemove", onMouseMove);

    // 7. Animation Loop
    let clock = new THREE.Clock();
    let animId;

    const animate = () => {
      animId = requestAnimationFrame(animate);
      const elapsedTime = clock.getElapsedTime();

      // Smooth flight interpolation (lerp)
      airplaneGroup.rotation.x += (targetRotX - airplaneGroup.rotation.x) * 0.06;
      airplaneGroup.rotation.y += (targetRotY - airplaneGroup.rotation.y) * 0.06;
      airplaneGroup.rotation.z += (targetRotZ - airplaneGroup.rotation.z) * 0.06;
      airplaneGroup.position.x += (targetPosX - airplaneGroup.position.x) * 0.06;
      airplaneGroup.position.y += (targetPosY + Math.sin(elapsedTime * 2.0) * 0.08 - airplaneGroup.position.y) * 0.06;

      // Engine fan rotation
      rightSpinner.rotation.z = elapsedTime * 20;
      leftSpinner.rotation.z = elapsedTime * 20;

      // Raycast detection
      raycaster.setFromCamera(mouseVec, camera);
      const intersects = raycaster.intersectObjects(interactiveMeshes, false);

      if (intersects.length > 0) {
        const hit = intersects[0].object;
        if (currentHoveredMesh !== hit) {
          // Reset previous mesh color
          if (currentHoveredMesh && currentHoveredMesh.material.userData?.originalColor) {
            currentHoveredMesh.material.color.copy(currentHoveredMesh.material.userData.originalColor);
            if (currentHoveredMesh.material.emissive) currentHoveredMesh.material.emissive.setHex(0x000000);
          }

          // Highlight new hovered mesh with Apple Electric Blue / Shimmer
          currentHoveredMesh = hit;
          if (hit.material.color) {
            hit.material.color.setHex(0x0071e3); // Apple Electric Blue
            if (hit.material.emissive) {
              hit.material.emissive.setHex(0x0051ba);
              hit.material.emissiveIntensity = 0.35;
            }
          }
          setHoveredPart(hit.userData);
        }
      } else {
        if (currentHoveredMesh) {
          if (currentHoveredMesh.material.userData?.originalColor) {
            currentHoveredMesh.material.color.copy(currentHoveredMesh.material.userData.originalColor);
            if (currentHoveredMesh.material.emissive) currentHoveredMesh.material.emissive.setHex(0x000000);
          }
          currentHoveredMesh = null;
          setHoveredPart(null);
        }
      }

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
        cursor: "crosshair",
        position: "relative",
      }}
    >
      {/* Floating Apple Telemetry HUD when hovering plane components */}
      {hoveredPart && (
        <div
          style={{
            position: "absolute",
            top: Math.min(Math.max(hudPos.y - 60, 20), 400),
            left: Math.min(Math.max(hudPos.x + 20, 20), 800),
            background: "rgba(255, 255, 255, 0.95)",
            backdropFilter: "blur(20px)",
            border: "1px solid rgba(0, 113, 227, 0.3)",
            borderRadius: 12,
            padding: "12px 18px",
            boxShadow: "0 10px 30px rgba(0,0,0,0.08), 0 0 15px rgba(0,113,227,0.15)",
            pointerEvents: "none",
            zIndex: 100,
            transition: "opacity 0.2s ease",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#0071e3" }} />
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, fontWeight: 700, color: "#0071e3", textTransform: "uppercase" }}>
              {hoveredPart.partName}
            </span>
          </div>
          <div style={{ fontSize: 13, color: "#1d1d1f", fontWeight: 600, marginTop: 4 }}>
            {hoveredPart.desc}
          </div>
          <div style={{ fontSize: 10, color: "#86868b", marginTop: 2, fontFamily: "var(--font-mono)" }}>
            ⚡ Real-time Telemetry Active
          </div>
        </div>
      )}
    </div>
  );
}
