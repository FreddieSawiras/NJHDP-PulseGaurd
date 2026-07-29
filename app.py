import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="3D Anatomical Heart", layout="wide")


def render_3d_heart():
    html_code = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            html, body { margin: 0; overflow: hidden; background: transparent; font-family: 'Plus Jakarta Sans', sans-serif; }
            #container { width: 100%; height: 100%; position: relative; }
            #infoBox {
                position: absolute; bottom: 20px; left: 50%; transform: translateX(-50%);
                background: rgba(8, 17, 31, 0.85); backdrop-filter: blur(12px);
                border: 1px solid rgba(0, 229, 255, 0.3); border-radius: 14px;
                padding: 12px 24px; color: #FFFFFF; font-size: 13px; font-weight: 600;
                text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.5);
                pointer-events: none; transition: all 0.2s ease;
                z-index: 10; max-width: 80%;
            }
            .part-tag { color: #00E5FF; font-weight: 700; }
            #loading {
                position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
                color: #00E5FF; font-size: 14px; font-weight: 700; letter-spacing: 0.05em;
                z-index: 5;
            }
            #hud {
                position: absolute; top: 16px; left: 16px;
                color: rgba(255,255,255,0.6); font-size: 11px; font-weight: 600;
                letter-spacing: 0.04em; z-index: 10;
            }
        </style>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
    </head>
    <body>
        <div id="container">
            <div id="loading">⚡ BUILDING 3D ANATOMICAL MODEL...</div>
            <div id="hud">HEART // INTERACTIVE MODEL</div>
            <div id="infoBox">💡 Drag to rotate • Scroll to zoom • Hover glowing nodes for details</div>
        </div>
        <script>
            const container = document.getElementById('container');
            const scene = new THREE.Scene();
            const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 1000);
            camera.position.set(0, 0.3, 7.5);

            const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
            renderer.setSize(container.clientWidth, container.clientHeight);
            renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
            container.appendChild(renderer.domElement);

            const controls = new THREE.OrbitControls(camera, renderer.domElement);
            controls.enableDamping = true;
            controls.dampingFactor = 0.06;
            controls.minDistance = 4;
            controls.maxDistance = 14;

            // ---------- Lighting ----------
            const ambientLight = new THREE.AmbientLight(0xffffff, 0.9);
            scene.add(ambientLight);

            const keyLight = new THREE.DirectionalLight(0xffffff, 1.4);
            keyLight.position.set(5, 8, 6);
            scene.add(keyLight);

            const rimLight = new THREE.DirectionalLight(0x00e5ff, 1.2);
            rimLight.position.set(-6, 2, -4);
            scene.add(rimLight);

            const glowLight = new THREE.PointLight(0xff4d6d, 3, 25, 2);
            glowLight.position.set(-3, -2, 4);
            scene.add(glowLight);

            const fillLight = new THREE.PointLight(0x00e5ff, 1.2, 20);
            fillLight.position.set(3, 3, -3);
            scene.add(fillLight);

            const heartGroup = new THREE.Group();
            scene.add(heartGroup);

            // ---------- Procedural anatomical heart shape ----------
            // Built from a heart-curve cross section, extruded and lathed for a
            // realistic rounded muscular silhouette instead of a generic sphere/icosahedron.
            function buildHeartGeometry() {
                const shape = new THREE.Shape();
                const x = 0, y = 0;
                shape.moveTo(x, y + 0.7);
                shape.bezierCurveTo(x, y + 1.1, x - 1.1, y + 1.3, x - 1.1, y + 0.55);
                shape.bezierCurveTo(x - 1.1, y - 0.15, x - 0.55, y - 0.85, x, y - 1.6);
                shape.bezierCurveTo(x + 0.55, y - 0.85, x + 1.1, y - 0.15, x + 1.1, y + 0.55);
                shape.bezierCurveTo(x + 1.1, y + 1.3, x, y + 1.1, x, y + 0.7);

                const extrudeSettings = {
                    steps: 4,
                    depth: 1.1,
                    bevelEnabled: true,
                    bevelThickness: 0.35,
                    bevelSize: 0.35,
                    bevelOffset: 0,
                    bevelSegments: 12,
                    curveSegments: 24
                };

                const geo = new THREE.ExtrudeGeometry(shape, extrudeSettings);
                geo.center();
                geo.computeVertexNormals();
                return geo;
            }

            const heartMat = new THREE.MeshPhysicalMaterial({
                color: 0xb5121b,
                roughness: 0.35,
                metalness: 0.05,
                clearcoat: 0.6,
                clearcoatRoughness: 0.3,
                sheen: 1.0,
                sheenColor: new THREE.Color(0xff4d6d),
                emissive: 0x2a0508,
                emissiveIntensity: 0.4
            });

            const heartMesh = new THREE.Mesh(buildHeartGeometry(), heartMat);
            heartMesh.rotation.x = Math.PI; // point downward, like an anatomical heart
            heartMesh.scale.set(1.15, 1.15, 1.0);
            heartGroup.add(heartMesh);

            // Subtle wireframe overlay for a "scan" feel
            const wireMat = new THREE.MeshBasicMaterial({ color: 0x00e5ff, wireframe: true, transparent: true, opacity: 0.08 });
            const wireMesh = new THREE.Mesh(heartMesh.geometry, wireMat);
            wireMesh.rotation.copy(heartMesh.rotation);
            wireMesh.scale.copy(heartMesh.scale);
            heartGroup.add(wireMesh);

            // Aorta / great vessel (simple curved tube arcing off the top)
            const vesselCurve = new THREE.CatmullRomCurve3([
                new THREE.Vector3(0.1, 1.5, 0.1),
                new THREE.Vector3(0.4, 2.0, -0.1),
                new THREE.Vector3(0.0, 2.3, -0.4),
                new THREE.Vector3(-0.5, 2.1, -0.3),
                new THREE.Vector3(-0.8, 1.6, 0.1)
            ]);
            const vesselGeo = new THREE.TubeGeometry(vesselCurve, 40, 0.22, 12, false);
            const vesselMat = new THREE.MeshPhysicalMaterial({ color: 0xd94f5c, roughness: 0.4, metalness: 0.1 });
            const vesselMesh = new THREE.Mesh(vesselGeo, vesselMat);
            heartGroup.add(vesselMesh);

            // ---------- Hotspots ----------
            const hotspotGeo = new THREE.SphereGeometry(0.09, 16, 16);
            const hotspotMat = new THREE.MeshBasicMaterial({ color: 0x00e5ff });

            const hotspots = [
                { pos: new THREE.Vector3(0.0, 2.15, -0.35), title: "AORTA", desc: "Main artery routing oxygenated blood to systemic circulation." },
                { pos: new THREE.Vector3(0.55, -0.5, 0.55), title: "LEFT VENTRICLE", desc: "Primary muscular pumping chamber sending blood to the body." },
                { pos: new THREE.Vector3(-0.85, 0.75, 0.35), title: "RIGHT ATRIUM", desc: "Receives deoxygenated blood returning from systemic veins." },
                { pos: new THREE.Vector3(0.15, 0.35, 0.85), title: "CORONARY ARTERY", desc: "Supplies oxygenated blood directly to cardiac tissue." },
                { pos: new THREE.Vector3(-0.4, -0.6, 0.6), title: "RIGHT VENTRICLE", desc: "Pumps deoxygenated blood to the lungs via the pulmonary artery." }
            ];

            const hotspotMeshes = [];
            hotspots.forEach(data => {
                const mesh = new THREE.Mesh(hotspotGeo, hotspotMat.clone());
                mesh.position.copy(data.pos);
                mesh.userData = data;
                heartGroup.add(mesh);
                hotspotMeshes.push(mesh);

                // faint outer glow ring
                const ringGeo = new THREE.RingGeometry(0.13, 0.16, 24);
                const ringMat = new THREE.MeshBasicMaterial({ color: 0x00e5ff, transparent: true, opacity: 0.5, side: THREE.DoubleSide });
                const ring = new THREE.Mesh(ringGeo, ringMat);
                ring.position.copy(data.pos);
                ring.lookAt(camera.position);
                heartGroup.add(ring);
                mesh.userData.ring = ring;
            });

            document.getElementById('loading').style.display = 'none';

            // ---------- Raycasting for interactivity ----------
            const raycaster = new THREE.Raycaster();
            const mouse = new THREE.Vector2();
            const infoBox = document.getElementById('infoBox');
            const defaultInfo = infoBox.innerHTML;

            function updatePointer(clientX, clientY) {
                const rect = renderer.domElement.getBoundingClientRect();
                mouse.x = ((clientX - rect.left) / rect.width) * 2 - 1;
                mouse.y = -((clientY - rect.top) / rect.height) * 2 + 1;

                raycaster.setFromCamera(mouse, camera);
                const intersects = raycaster.intersectObjects(hotspotMeshes);

                if (intersects.length > 0) {
                    const data = intersects[0].object.userData;
                    infoBox.innerHTML = `<span class="part-tag">📍 ${data.title}:</span> ${data.desc}`;
                    container.style.cursor = 'pointer';
                } else {
                    infoBox.innerHTML = defaultInfo;
                    container.style.cursor = 'default';
                }
            }

            window.addEventListener('mousemove', (e) => updatePointer(e.clientX, e.clientY));
            window.addEventListener('touchmove', (e) => {
                if (e.touches.length > 0) updatePointer(e.touches[0].clientX, e.touches[0].clientY);
            }, { passive: true });

            // ---------- Heartbeat pulse animation ----------
            const clock = new THREE.Clock();
            function animate() {
                requestAnimationFrame(animate);
                const t = clock.getElapsedTime();

                // Realistic double-thump pulse (lub-dub)
                const pulse = 1 + Math.sin(t * 4) * 0.035 + Math.max(0, Math.sin(t * 8)) * 0.02;
                heartMesh.scale.set(1.15 * pulse, 1.15 * pulse, 1.0 * pulse);
                wireMesh.scale.copy(heartMesh.scale);

                heartGroup.rotation.y += 0.004;

                hotspotMeshes.forEach(m => {
                    const s = 1 + Math.sin(t * 6 + m.position.x) * 0.25;
                    m.scale.set(s, s, s);
                    if (m.userData.ring) m.userData.ring.lookAt(camera.position);
                });

                glowLight.intensity = 2.5 + Math.sin(t * 4) * 1.0;

                controls.update();
                renderer.render(scene, camera);
            }
            animate();

            window.addEventListener('resize', () => {
                camera.aspect = container.clientWidth / container.clientHeight;
                camera.updateProjectionMatrix();
                renderer.setSize(container.clientWidth, container.clientHeight);
            });
        </script>
    </body>
    </html>
    """
    components.html(html_code, height=560)


# ---------------- Streamlit page ----------------
st.title("🫀 3D Anatomical Heart")
st.caption("Drag to rotate, scroll to zoom, and hover the glowing nodes to explore each structure.")

render_3d_heart()

with st.expander("About this model"):
    st.write(
        "This heart is built procedurally in Three.js (no external model download), "
        "so it always renders reliably. It includes a beating pulse animation, "
        "a curved aorta, and interactive hotspots for key anatomical structures."
    )
