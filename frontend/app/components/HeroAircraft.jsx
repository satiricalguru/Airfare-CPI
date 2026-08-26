"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";

export default function HeroAircraft({ isHovered, onHoverChange }) {
  const mountRef = useRef(null);

  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    // 1. Scene & Camera setup
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(
      45,
      container.clientWidth / container.clientHeight,
      0.1,
      1000
    );
    camera.position.set(0, 1.5, 9);

    // 2. Renderer setup
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    container.appendChild(renderer.domElement);

    // 3. Lighting
    const ambientLight = new THREE.AmbientLight(0x0f274a, 1.8);
    scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0x4cd7f6, 3.5);
    dirLight.position.set(5, 8, 5);
    scene.add(dirLight);

    const goldRimLight = new THREE.PointLight(0xf9bd22, 4.0, 15);
    goldRimLight.position.set(-6, 3, -4);
    scene.add(goldRimLight);

    const cyanUnderGlow = new THREE.PointLight(0x00ffff, 5.0, 12);
    cyanUnderGlow.position.set(0, -3, 2);
    scene.add(cyanUnderGlow);

    // 4. Procedural Aircraft Group
    const airplaneGroup = new THREE.Group();
    scene.add(airplaneGroup);

    // Materials
    const bodyMaterial = new THREE.MeshPhysicalMaterial({
      color: 0x0a2240,
      metalness: 0.85,
      roughness: 0.2,
      clearcoat: 1.0,
      clearcoatRoughness: 0.1,
      reflectivity: 0.9,
    });

    const glassMaterial = new THREE.MeshPhysicalMaterial({
      color: 0x06b6d4,
      metalness: 0.9,
      roughness: 0.05,
      transmission: 0.6,
      opacity: 0.95,
      transparent: true,
      emissive: 0x06b6d4,
      emissiveIntensity: 0.4,
    });

    const glowMaterial = new THREE.MeshBasicMaterial({
      color: 0x00f0ff,
      wireframe: true,
      transparent: true,
      opacity: 0.3,
    });

    const goldMaterial = new THREE.MeshStandardMaterial({
      color: 0xf9bd22,
      metalness: 0.9,
      roughness: 0.3,
    });

    // Fuselage (Sleek aerodynamic body)
    const bodyGeometry = new THREE.ConeGeometry(0.55, 4.5, 32);
    const fuselage = new THREE.Mesh(bodyGeometry, bodyMaterial);
    fuselage.rotation.x = Math.PI / 2;
    airplaneGroup.add(fuselage);

    // Cockpit Glass
    const cockpitGeo = new THREE.SphereGeometry(0.35, 16, 16);
    cockpitGeo.scale(0.8, 0.4, 2.2);
    const cockpit = new THREE.Mesh(cockpitGeo, glassMaterial);
    cockpit.position.set(0, 0.32, 0.8);
    airplaneGroup.add(cockpit);

    // Main Delta Wings
    const wingShape = new THREE.Shape();
    wingShape.moveTo(0, 0);
    wingShape.lineTo(3.2, -1.8);
    wingShape.lineTo(3.0, -2.4);
    wingShape.lineTo(0, -1.6);
    wingShape.closePath();

    const extrudeSettings = { depth: 0.06, bevelEnabled: true, bevelSegments: 2, steps: 1, bevelSize: 0.02, bevelThickness: 0.02 };
    const wingGeometry = new THREE.ExtrudeGeometry(wingShape, extrudeSettings);

    const rightWing = new THREE.Mesh(wingGeometry, bodyMaterial);
    rightWing.position.set(0, 0.02, 0.2);
    rightWing.rotation.x = Math.PI / 2;
    airplaneGroup.add(rightWing);

    const leftWing = rightWing.clone();
    leftWing.scale.x = -1;
    airplaneGroup.add(leftWing);

    // Wingtip Gold Strakes
    const strakeGeo = new THREE.BoxGeometry(0.08, 0.4, 0.8);
    const rightStrake = new THREE.Mesh(strakeGeo, goldMaterial);
    rightStrake.position.set(3.1, 0.15, -1.9);
    airplaneGroup.add(rightStrake);

    const leftStrake = rightStrake.clone();
    leftStrake.position.x = -3.1;
    airplaneGroup.add(leftStrake);

    // Vertical Stabilizer / Tail Fin
    const tailShape = new THREE.Shape();
    tailShape.moveTo(0, 0);
    tailShape.lineTo(0.05, 1.4);
    tailShape.lineTo(0.05, 1.3);
    tailShape.lineTo(1.1, 0);
    tailShape.closePath();
    const tailGeo = new THREE.ExtrudeGeometry(tailShape, extrudeSettings);
    const tailFin = new THREE.Mesh(tailGeo, bodyMaterial);
    tailFin.position.set(0, 0.2, -1.4);
    tailFin.rotation.y = -Math.PI / 2;
    airplaneGroup.add(tailFin);

    // Twin Engines
    const engineGeo = new THREE.CylinderGeometry(0.24, 0.28, 1.6, 24);
    const rightEngine = new THREE.Mesh(engineGeo, bodyMaterial);
    rightEngine.position.set(0.9, -0.15, -0.6);
    rightEngine.rotation.x = Math.PI / 2;
    airplaneGroup.add(rightEngine);

    const leftEngine = rightEngine.clone();
    leftEngine.position.x = -0.9;
    airplaneGroup.add(leftEngine);

    // Glowing Afterburner Exhausts
    const exhaustGeo = new THREE.SphereGeometry(0.2, 16, 16);
    const exhaustMat = new THREE.MeshBasicMaterial({ color: 0x00f0ff });
    const rightExhaust = new THREE.Mesh(exhaustGeo, exhaustMat);
    rightExhaust.position.set(0.9, -0.15, -1.45);
    rightExhaust.scale.set(1, 1, 1.8);
    airplaneGroup.add(rightExhaust);

    const leftExhaust = rightExhaust.clone();
    leftExhaust.position.x = -0.9;
    airplaneGroup.add(leftExhaust);

    // Halo Data Orbit Ring
    const ringGeo = new THREE.TorusGeometry(3.6, 0.02, 16, 100);
    const ringMat = new THREE.MeshBasicMaterial({ color: 0x06b6d4, transparent: true, opacity: 0.4 });
    const orbitRing = new THREE.Mesh(ringGeo, ringMat);
    orbitRing.rotation.x = Math.PI / 3;
    airplaneGroup.add(orbitRing);

    // Floating Background Particle Dust
    const particleCount = 280;
    const particleGeo = new THREE.BufferGeometry();
    const particlePositions = new Float32Array(particleCount * 3);
    for (let i = 0; i < particleCount * 3; i += 3) {
      particlePositions[i] = (Math.random() - 0.5) * 18;
      particlePositions[i + 1] = (Math.random() - 0.5) * 14;
      particlePositions[i + 2] = (Math.random() - 0.5) * 14;
    }
    particleGeo.setAttribute("position", new THREE.BufferAttribute(particlePositions, 3));
    const particleMat = new THREE.PointsMaterial({
      color: 0x3b82f6,
      size: 0.06,
      transparent: true,
      opacity: 0.65,
    });
    const particles = new THREE.Points(particleGeo, particleMat);
    scene.add(particles);

    // Initial Aircraft Angle
    airplaneGroup.position.set(0.6, 0.1, 0);
    airplaneGroup.rotation.set(-0.25, 0.65, 0.15);

    // 5. Mouse Interaction & Spring Physics
    let targetRotX = -0.25;
    let targetRotY = 0.65;
    let targetRotZ = 0.15;
    let targetPosX = 0.6;
    let targetPosY = 0.1;

    const handleMouseMove = (e) => {
      const rect = container.getBoundingClientRect();
      const x = (e.clientX - rect.left) / rect.width - 0.5;
      const y = (e.clientY - rect.top) / rect.height - 0.5;

      targetRotY = 0.65 + x * 0.95;
      targetRotX = -0.25 - y * 0.75;
      targetRotZ = 0.15 - x * 0.35;
      targetPosX = 0.6 + x * 0.6;
      targetPosY = 0.1 - y * 0.4;
    };

    window.addEventListener("mousemove", handleMouseMove);

    // 6. Animation Loop
    let clock = new THREE.Clock();
    let animId;

    const animate = () => {
      animId = requestAnimationFrame(animate);
      const elapsedTime = clock.getElapsedTime();

      // Smooth lerp towards mouse target
      airplaneGroup.rotation.x += (targetRotX - airplaneGroup.rotation.x) * 0.05;
      airplaneGroup.rotation.y += (targetRotY - airplaneGroup.rotation.y) * 0.05;
      airplaneGroup.rotation.z += (targetRotZ - airplaneGroup.rotation.z) * 0.05;
      airplaneGroup.position.x += (targetPosX - airplaneGroup.position.x) * 0.05;
      airplaneGroup.position.y += (targetPosY + Math.sin(elapsedTime * 1.8) * 0.12 - airplaneGroup.position.y) * 0.05;

      // Orbit ring spin
      orbitRing.rotation.z = elapsedTime * 0.3;

      // Particle subtle drift
      particles.rotation.y = elapsedTime * 0.02;

      // Engine pulse
      const pulse = 1.0 + Math.sin(elapsedTime * 8) * 0.25;
      rightExhaust.scale.set(pulse, pulse, 1.8 * pulse);
      leftExhaust.scale.set(pulse, pulse, 1.8 * pulse);

      renderer.render(scene, camera);
    };

    animate();

    // 7. Resize handling
    const handleResize = () => {
      if (!container) return;
      camera.aspect = container.clientWidth / container.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(container.clientWidth, container.clientHeight);
    };

    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("resize", handleResize);
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
      onMouseEnter={() => onHoverChange && onHoverChange(true)}
      onMouseLeave={() => onHoverChange && onHoverChange(false)}
      style={{
        width: "100%",
        height: "100%",
        cursor: "pointer",
        position: "relative",
      }}
    />
  );
}
