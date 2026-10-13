import * as THREE from 'three';
import {OrbitControls} from 'three/examples/jsm/controls/OrbitControls.js';
import {RoomEnvironment} from 'three/examples/jsm/environments/RoomEnvironment.js';
import {GLTFLoader} from 'three/examples/jsm/loaders/GLTFLoader.js';
import {DRACOLoader} from 'three/examples/jsm/loaders/DRACOLoader.js';
import {MeshoptDecoder} from 'three/examples/jsm/libs/meshopt_decoder.module.js';
import {OBJLoader} from 'three/examples/jsm/loaders/OBJLoader.js';
import {MTLLoader} from 'three/examples/jsm/loaders/MTLLoader.js';
import {STLLoader} from 'three/examples/jsm/loaders/STLLoader.js';
import {PLYLoader} from 'three/examples/jsm/loaders/PLYLoader.js';
import {FBXLoader} from 'three/examples/jsm/loaders/FBXLoader.js';
import {ColladaLoader} from 'three/examples/jsm/loaders/ColladaLoader.js';
import {TDSLoader} from 'three/examples/jsm/loaders/TDSLoader.js';
import {ThreeMFLoader} from 'three/examples/jsm/loaders/3MFLoader.js';
import {VRMLLoader} from 'three/examples/jsm/loaders/VRMLLoader.js';
import {VTKLoader} from 'three/examples/jsm/loaders/VTKLoader.js';
import {PCDLoader} from 'three/examples/jsm/loaders/PCDLoader.js';
import {XYZLoader} from 'three/examples/jsm/loaders/XYZLoader.js';
import {AMFLoader} from 'three/examples/jsm/loaders/AMFLoader.js';
import {USDZLoader} from 'three/examples/jsm/loaders/USDZLoader.js';

const $ = id => document.getElementById(id);
const canvas = $('c');
const renderer = new THREE.WebGLRenderer({canvas, antialias: true});
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.toneMapping = THREE.ACESFilmicToneMapping;
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(45, 1, 0.01, 1000);
const controls = new OrbitControls(camera, canvas);
controls.enableDamping = true;
controls.screenSpacePanning = true;
const pmrem = new THREE.PMREMGenerator(renderer);
const envMap = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
const hemi = new THREE.HemisphereLight(0xffffff, 0x444455, 0.6);
const dir = new THREE.DirectionalLight(0xffffff, 1.5);
camera.add(dir); scene.add(camera, hemi);
dir.position.set(2, 3, 4);
const grid = new THREE.GridHelper(10, 20, 0x666a75, 0x33363f);
scene.add(grid);

const BGS = [0x14161a, 0xf0f1f3, 0x4a5d73, 0x000000];
let bgIdx = 0, lightMode = 0, wire = false, root = null, mixer = null, actions = [], playing = true;
const clock = new THREE.Clock();
const setBg = () => { scene.background = new THREE.Color(BGS[bgIdx]); document.body.style.background = '#' + BGS[bgIdx].toString(16).padStart(6, '0'); };
const setLight = () => {
  scene.environment = lightMode === 1 ? null : envMap;
  hemi.intensity = lightMode === 1 ? 1.2 : 0.4;
  dir.intensity = lightMode === 2 ? 0 : 1.5;
};
setBg(); setLight();

function resize() {
  const w = innerWidth, h = innerHeight;
  renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix();
}
addEventListener('resize', resize); resize();

function msg(t) { const m = $('msg'); if (t) { m.textContent = t; m.classList.add('show'); } else m.classList.remove('show'); }
function disposeRoot() {
  if (!root) return;
  scene.remove(root);
  root.traverse(o => {
    if (o.geometry) o.geometry.dispose();
    const ms = o.material ? [].concat(o.material) : [];
    ms.forEach(m => { for (const k in m) if (m[k] && m[k].isTexture) m[k].dispose(); m.dispose(); });
  });
  root = null; mixer = null; actions = [];
}

function frame() {
  const box = new THREE.Box3().setFromObject(root);
  if (box.isEmpty()) return;
  const size = box.getSize(new THREE.Vector3()), c = box.getCenter(new THREE.Vector3());
  const r = Math.max(size.x, size.y, size.z) || 1;
  root.position.sub(c); root.position.y += size.y / 2; // pose sur la grille
  grid.scale.setScalar(Math.max(r / 5, 0.001));
  const d = r * 1.8;
  camera.near = r / 200; camera.far = r * 200; camera.updateProjectionMatrix();
  camera.position.set(d * 0.8, d * 0.6 + size.y / 2, d);
  controls.target.set(0, size.y / 2, 0);
  controls.minDistance = r * 0.05; controls.maxDistance = r * 50;
  controls.update();
}
$('bReset').onclick = () => root && (root.position.set(0, 0, 0), frame());

function applyWire() { root && root.traverse(o => o.material && [].concat(o.material).forEach(m => m.wireframe = wire)); }

function setModel(obj, animations) {
  disposeRoot();
  root = new THREE.Group(); root.add(obj); scene.add(root);
  let tris = 0, meshes = 0;
  obj.traverse(o => {
    if (o.isPoints && !o.material.map) o.material.size = o.material.size || 2;
    if (o.isMesh || o.isPoints) {
      meshes++;
      if (o.isMesh && !o.material) o.material = new THREE.MeshStandardMaterial({color: 0xbbbbbb});
      if (o.isMesh && o.geometry) tris += (o.geometry.index ? o.geometry.index.count : o.geometry.attributes.position.count) / 3;
    }
  });
  root.userData = {tris, meshes};
  applyWire(); frame();
  actions = [];
  if (animations && animations.length) {
    mixer = new THREE.AnimationMixer(obj);
    actions = animations.map(a => mixer.clipAction(a)); actions.forEach(a => a.play()); playing = true;
    $('bAnim').style.display = ''; $('bAnim').firstChild.textContent = '⏸';
  } else $('bAnim').style.display = 'none';
}

const defaultMat = () => new THREE.MeshStandardMaterial({color: 0xc8ccd4, roughness: 0.55, metalness: 0.1, side: THREE.DoubleSide});
function fromGeometry(g) {
  if (!g.attributes.normal && g.index !== undefined) g.computeVertexNormals();
  if (g.index === null && !g.attributes.normal && !g.attributes.color) g.computeVertexNormals();
  const hasIdx = g.index || g.attributes.position.count % 3 === 0;
  const faces = g.index ? g.index.count > 0 : (g.attributes.position.count > 0);
  // PLY / XYZ / PCD sans faces => nuage de points
  if (g.userData && g.userData.points) return new THREE.Points(g, new THREE.PointsMaterial({size: 2, sizeAttenuation: false, vertexColors: !!g.attributes.color, color: g.attributes.color ? 0xffffff : 0xc8ccd4}));
  const m = defaultMat(); if (g.attributes.color) m.vertexColors = true;
  return new THREE.Mesh(g, m);
}

const ext = n => (n.split('.').pop() || '').toLowerCase();
const MODEL_EXT = ['glb','gltf','obj','stl','ply','fbx','dae','3ds','3mf','wrl','vrml','vtk','pcd','xyz','amf','usdz'];
const draco = new DRACOLoader().setDecoderPath('draco/');

async function loadFiles(files) {
  const list = [...files];
  const main = list.find(f => MODEL_EXT.includes(ext(f.name))) || list[0];
  if (!main) return;
  msg('Chargement de ' + main.name + '…');
  const urls = {};
  list.forEach(f => urls[f.name.toLowerCase()] = URL.createObjectURL(f));
  const mgr = new THREE.LoadingManager();
  mgr.setURLModifier(u => {
    if (/^(blob|data):/.test(u)) return u;
    const base = decodeURIComponent(u.split(/[?#]/)[0].split('/').pop()).toLowerCase();
    return urls[base] || u;
  });
  const e = ext(main.name);
  const buf = () => main.arrayBuffer();
  const txt = () => main.text();
  try {
    let obj, anims;
    if (e === 'glb' || e === 'gltf') {
      const l = new GLTFLoader(mgr).setDRACOLoader(draco).setMeshoptDecoder(MeshoptDecoder);
      const g = await l.parseAsync(e === 'glb' ? await buf() : await txt(), '');
      obj = g.scene; anims = g.animations;
    } else if (e === 'obj') {
      const l = new OBJLoader(mgr);
      const mtlF = list.find(f => ext(f.name) === 'mtl');
      if (mtlF) { const m = new MTLLoader(mgr).parse(await mtlF.text(), ''); m.preload(); l.setMaterials(m); }
      obj = l.parse(await txt());
      obj.traverse(o => { if (o.isMesh && !mtlF) o.material = defaultMat(); });
    } else if (e === 'stl') obj = fromGeometry(new STLLoader(mgr).parse(await buf()));
    else if (e === 'ply') { const g = new PLYLoader(mgr).parse(await buf()); if (!g.index || g.index.count === 0) g.userData.points = true; obj = fromGeometry(g); }
    else if (e === 'fbx') { obj = new FBXLoader(mgr).parse(await buf(), ''); anims = obj.animations; }
    else if (e === 'dae') { const c = new ColladaLoader(mgr).parse(await txt(), ''); obj = c.scene; anims = c.animations; }
    else if (e === '3ds') obj = new TDSLoader(mgr).parse(await buf(), '');
    else if (e === '3mf') obj = new ThreeMFLoader(mgr).parse(await buf());
    else if (e === 'wrl' || e === 'vrml') obj = new VRMLLoader(mgr).parse(await txt(), '');
    else if (e === 'vtk') { const g = new VTKLoader(mgr).parse(await buf()); obj = fromGeometry(g); }
    else if (e === 'pcd') obj = new PCDLoader(mgr).parse(await buf());
    else if (e === 'xyz') { const g = new XYZLoader(mgr).parse(await txt()); g.userData.points = true; obj = fromGeometry(g); }
    else if (e === 'amf') obj = new AMFLoader(mgr).parse(await buf());
    else if (e === 'usdz') obj = await new USDZLoader(mgr).parse(await buf());
    else throw new Error('Format non pris en charge : .' + e);
    if (!obj) throw new Error('Fichier vide ou illisible');
    setModel(obj, anims);
    $('info').textContent = main.name + ' — ' + Math.round(root.userData.tris).toLocaleString('fr') + ' triangles, ' + root.userData.meshes + ' objet(s)';
    msg('');
  } catch (err) {
    console.error(err);
    msg('Impossible de lire ce fichier.\n' + (err.message || err) + '\n\nFormats : ' + MODEL_EXT.join(', ') + '\n(OBJ/GLTF : sélectionnez aussi .mtl / .bin / textures)');
    setTimeout(() => msg(''), 6000);
  }
  setTimeout(() => Object.values(urls).forEach(URL.revokeObjectURL), 60000);
}

// UI
const file = $('file');
$('bOpen').onclick = () => file.click();
file.onchange = () => { if (file.files.length) loadFiles(file.files); file.value = ''; };
const toggle = (id, on) => $(id).classList.toggle('on', on);
$('bRot').onclick = () => { controls.autoRotate = !controls.autoRotate; controls.autoRotateSpeed = 2; toggle('bRot', controls.autoRotate); };
$('bWire').onclick = () => { wire = !wire; toggle('bWire', wire); applyWire(); };
$('bGrid').onclick = () => { grid.visible = !grid.visible; toggle('bGrid', grid.visible); };
$('bBg').onclick = () => { bgIdx = (bgIdx + 1) % BGS.length; setBg(); };
$('bLight').onclick = () => { lightMode = (lightMode + 1) % 3; setLight(); };
$('bAnim').onclick = () => { playing = !playing; actions.forEach(a => a.paused = !playing); $('bAnim').firstChild.textContent = playing ? '⏸' : '▶'; };

renderer.setAnimationLoop(() => {
  const dt = clock.getDelta();
  if (mixer && playing) mixer.update(dt);
  controls.update(); renderer.render(scene, camera);
});

// Modèle de démonstration
(function demo() {
  const g = new THREE.Group();
  const knot = new THREE.Mesh(new THREE.TorusKnotGeometry(1, 0.32, 220, 36), new THREE.MeshStandardMaterial({color: 0x4f9dff, metalness: 0.6, roughness: 0.25}));
  g.add(knot);
  setModel(g);
  $('info').textContent = 'Démo — touchez « Ouvrir » pour charger un fichier 3D';
})();

// Fichier ouvert depuis une autre app (Ouvrir avec…)
const q = new URLSearchParams(location.search);
if (q.get('open')) {
  fetch('open/' + encodeURIComponent(q.get('name') || 'model')).then(r => r.blob())
    .then(b => loadFiles([new File([b], q.get('name') || 'model.glb')]));
}
