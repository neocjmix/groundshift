import * as THREE from 'three';
import { nearestBackground, panoramaRay, parseBackgroundMesh, type BackgroundMode, type LoadedBackground } from './background';

/** Presentation-only backdrop. Render before GS, then clear depth: never collision/geometry proof. */
export class BackgroundLayer {
  private scene = new THREE.Scene();
  private current = -1;
  private pending = -1;
  private mode: BackgroundMode = 'gs';
  private request?: AbortController;
  private generation = 0;
  private disposed = false;
  private sphere?: THREE.Mesh<THREE.BufferGeometry, THREE.MeshBasicMaterial>;
  private shell?: THREE.Mesh<THREE.BufferGeometry, THREE.MeshBasicMaterial>;
  private texture?: THREE.Texture;
  private failed = -1;
  public source = '';
  constructor(private background: LoadedBackground, private status: (message: string) => void) {}

  setMode(mode: BackgroundMode) {
    this.mode = mode;
    this.failed = -1;
    if (mode !== 'gs' && this.current >= 0) this.status(`Source photo ${this.source} · ${mode === 'depth-shell' ? 'estimated depth shell + panorama fallback' : 'infinite panorama'} · presentation only`);
    if (mode === 'gs') {
      this.generation++;
      this.request?.abort(); this.pending = -1;
      this.status('GS only · background disabled');
    }
  }

  update(camera: THREE.PerspectiveCamera) {
    if (this.mode === 'gs' || this.disposed) return;
    const index = nearestBackground(this.background.views, camera.position.toArray(), this.current);
    if (index !== this.current && index !== this.pending && index !== this.failed) void this.load(index);
    if (this.sphere) {
      this.sphere.position.copy(camera.position);
      this.sphere.scale.setScalar(camera.far * .8);
      this.sphere.visible = true;
    }
    if (this.shell) this.shell.visible = this.mode === 'depth-shell';
  }

  render(renderer: THREE.WebGLRenderer, camera: THREE.PerspectiveCamera) {
    if (this.mode !== 'gs' && this.sphere) renderer.render(this.scene, camera);
  }

  private clear() {
    for (const mesh of [this.sphere, this.shell]) if (mesh) {
      this.scene.remove(mesh); mesh.geometry.dispose(); mesh.material.dispose();
    }
    this.texture?.dispose(); this.texture = undefined; this.sphere = undefined; this.shell = undefined;
  }

  private async load(index: number) {
    const generation = ++this.generation;
    this.request?.abort(); const request = this.request = new AbortController(); this.pending = index;
    const view = this.background.views[index]; let texture: THREE.Texture | undefined;
    this.status(`Loading source-photo background · ${view.id}`);
    try {
      const image = await fetch(view.imageUrl, { signal: request.signal });
      if (!image.ok) throw new Error(`Background image HTTP ${image.status}`);
      const url = URL.createObjectURL(await image.blob());
      try { texture = await new THREE.TextureLoader().loadAsync(url); }
      finally { URL.revokeObjectURL(url); }
      request.signal.throwIfAborted();
      let shellGeometry: THREE.BufferGeometry | undefined;
      if (view.meshUrl) {
        const response = await fetch(view.meshUrl, { signal: request.signal });
        if (!response.ok) throw new Error(`Background depth shell HTTP ${response.status}`);
        const mesh = parseBackgroundMesh(await response.json());
        request.signal.throwIfAborted();
        shellGeometry = new THREE.BufferGeometry();
        shellGeometry.setAttribute('position', new THREE.Float32BufferAttribute(mesh.positions, 3));
        shellGeometry.setAttribute('uv', new THREE.Float32BufferAttribute(mesh.uvs, 2));
        shellGeometry.setIndex(mesh.indices);
      }
      if (this.disposed || generation !== this.generation) { shellGeometry?.dispose(); texture.dispose(); return; }
      texture.colorSpace = THREE.SRGBColorSpace;
      texture.wrapS = THREE.RepeatWrapping;
      texture.wrapT = THREE.ClampToEdgeWrapping;
      const positions: number[] = [], uvs: number[] = [], indices: number[] = [];
      const columns = 96, rows = 48;
      for (let y = 0; y <= rows; y++) for (let x = 0; x <= columns; x++) {
        positions.push(...panoramaRay(x / columns, y / rows)); uvs.push(x / columns, 1 - y / rows);
      }
      for (let y = 0; y < rows; y++) for (let x = 0; x < columns; x++) {
        const a = y * (columns + 1) + x, b = a + columns + 1;
        indices.push(a, b, a + 1, a + 1, b, b + 1);
      }
      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
      geometry.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2)); geometry.setIndex(indices);
      const material = () => new THREE.MeshBasicMaterial({ map: texture, side: THREE.DoubleSide, depthWrite: false, toneMapped: false });
      this.clear(); this.texture = texture;
      this.sphere = new THREE.Mesh(geometry, material()); this.sphere.renderOrder = -100;
      const matrix = new THREE.Matrix4().set(...view.panoramaToWorld.flat() as Parameters<THREE.Matrix4['set']>);
      this.sphere.quaternion.setFromRotationMatrix(matrix);
      this.scene.add(this.sphere);
      if (shellGeometry) {
        this.shell = new THREE.Mesh(shellGeometry, material()); this.shell.renderOrder = -99;
        this.shell.material.depthWrite = true;
        this.shell.visible = this.mode === 'depth-shell'; this.scene.add(this.shell);
      }
      this.current = index; this.source = view.id;
      this.status(`Source photo ${view.id} · ${this.mode === 'depth-shell' ? 'estimated depth shell + panorama fallback' : 'infinite panorama'} · presentation only`);
    } catch (error) {
      texture?.dispose();
      if (!request.signal.aborted && !this.disposed && generation === this.generation) {
        this.failed = index;
        this.status(`Background FAIL · ${error instanceof Error ? error.message : String(error)}. GS is unchanged; select GS only or retry the mode.`);
      }
    } finally { if (generation === this.generation) this.pending = -1; }
  }
  dispose() { this.disposed = true; this.generation++; this.request?.abort(); this.clear(); }
}
