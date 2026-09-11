import React, { Suspense, Component, useState } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, ContactShadows, Html } from '@react-three/drei';
import { BabaModel, type BabaSpeechState } from './BabaModel';
import { RotateCw, Sparkles, AlertCircle } from 'lucide-react';

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback: React.ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
}

class WebGLErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.warn('WebGL or 3D scene failed, falling back to 2D view:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback;
    }
    return this.props.children;
  }
}

// Loading indicator inside the 3D canvas
const SceneLoader: React.FC = () => (
  <Html center>
    <div className="flex flex-col items-center justify-center p-4 bg-white/90 backdrop-blur-md rounded-2xl shadow-lg border border-[#E7E0D3] space-y-2">
      <div className="w-8 h-8 border-3 border-[#D97706]/20 border-t-[#D97706] rounded-full animate-spin" />
      <span className="text-xs font-serif font-semibold text-[#1E1B4B]">
        Awakening Baba Ji 3D Avatar...
      </span>
      <span className="text-[10px] text-[#786F63]">Loading GLTF Mesh & Rig</span>
    </div>
  </Html>
);

interface BabaSceneProps {
  isSpeaking?: boolean;
  systemState?: BabaSpeechState;
}

export const BabaScene: React.FC<BabaSceneProps> = ({ isSpeaking = false, systemState = 'IDLE' }) => {
  const [controlsRef, setControlsRef] = useState<any>(null);

  const resetCamera = () => {
    if (controlsRef) {
      controlsRef.reset();
    }
  };

  const fallback2D = (
    <div className="w-full h-full relative flex items-center justify-center bg-cover bg-center p-6"
      style={{ backgroundImage: "url('/assets/baba-study-environment.jpg')" }}
    >
      <div className="relative max-w-md w-full rounded-2xl overflow-hidden shadow-2xl border border-[#E7E0D3] bg-white/95 backdrop-blur-sm">
        <img
          src="/assets/baba-portrait.jpg"
          alt="Baba Ji - Ayurvedic Legal Scholar"
          className="w-full h-80 object-cover object-top"
        />
        <div className="p-4 bg-white border-t border-[#E7E0D3]">
          <div className="flex items-center space-x-2 text-[#D97706] mb-1">
            <AlertCircle className="w-4 h-4" />
            <span className="text-xs font-semibold">2D High-Res Fallback Active</span>
          </div>
          <p className="text-xs text-[#574F45]">
            Baba Ji — Traditional Knowledge Legal Scholar & Ayush Sahayak.
          </p>
        </div>
      </div>
    </div>
  );

  return (
    <WebGLErrorBoundary fallback={fallback2D}>
      {/* Full-bleed, cover-fit background featuring the Interior Study (warm wood shelves, Sanskrit text, desk) */}
      <div
        className="relative w-full h-full overflow-hidden bg-cover bg-center bg-no-repeat select-none"
        style={{ backgroundImage: "url('/assets/baba-study-environment.jpg')" }}
      >
        {/* Subtle warm atmospheric lighting gradient overlay behind 3D avatar */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/25 via-transparent to-black/15 pointer-events-none" />

        {/* Interactive 3D Camera Controls Hint Pill */}
        <div className="absolute top-4 right-4 z-10 flex items-center space-x-2">
          <button
            onClick={resetCamera}
            className="flex items-center space-x-1.5 px-3 py-1.5 bg-white/90 hover:bg-white text-[#1E1B4B] border border-[#E7E0D3] rounded-full text-xs font-semibold shadow-xs hover:border-[#D97706] transition-all backdrop-blur-md cursor-pointer"
            title="Reset 3D Camera View"
          >
            <RotateCw className="w-3.5 h-3.5 text-[#D97706]" />
            <span>Reset View</span>
          </button>

          <div className="hidden sm:flex items-center space-x-1.5 px-3 py-1.5 bg-white/90 text-[#574F45] border border-[#E7E0D3] rounded-full text-xs font-medium shadow-xs backdrop-blur-md">
            <Sparkles className="w-3.5 h-3.5 text-[#D97706]" />
            <span>Drag to rotate Baba in 3D</span>
          </div>
        </div>

        {/* The 3D Canvas with WebGL & OrbitControls rendered directly over full-bleed study background */}
        <Canvas
          shadows
          camera={{ position: [0, 0.15, 2.5], fov: 43 }}
          className="w-full h-full cursor-grab active:cursor-grabbing"
          gl={{ antialias: true, alpha: true }}
        >
          <OrbitControls
            ref={(ref) => setControlsRef(ref)}
            makeDefault
            enablePan={true}
            enableZoom={true}
            enableRotate={true}
            minDistance={1.2}
            maxDistance={4.2}
            maxPolarAngle={Math.PI / 2 + 0.05}
            target={[0, 0.0, 0]}
            dampingFactor={0.08}
          />

          {/* Lighting Rig tailored for the scholar's study */}
          <ambientLight intensity={1.1} color="#FFFBF2" />
          <directionalLight
            position={[2.5, 4.0, 3.0]}
            intensity={1.8}
            color="#FFF6EB"
            castShadow
            shadow-mapSize-width={1024}
            shadow-mapSize-height={1024}
            shadow-bias={-0.0001}
          />
          <directionalLight position={[-2.5, 2.0, 2.0]} intensity={0.8} color="#FFEAD5" />
          <pointLight position={[0, 3.0, -1.8]} intensity={1.2} color="#FFDF9E" />
          {/* Warm Diya flame glow */}
          <pointLight position={[0.7, -0.3, 0.8]} intensity={1.2} color="#D97706" distance={3.5} />

          {/* Floor Contact Shadows */}
          <ContactShadows
            position={[0, -0.94, 0]}
            opacity={0.7}
            scale={4}
            blur={2.0}
            far={2.5}
            color="#2A1B0E"
          />

          {/* Main 3D Baba character */}
          <Suspense fallback={<SceneLoader />}>
            <BabaModel isSpeaking={isSpeaking} state={systemState} />
          </Suspense>
        </Canvas>
      </div>
    </WebGLErrorBoundary>
  );
};
