import React, { useCallback, useEffect, useRef } from 'react';

// NyayaSetu earthy palette as RGB strings
const COLORS = [
  '194, 123, 58',   // Mitti (clay brown)
  '245, 158, 11',   // Haldi (turmeric gold)
  '212, 154, 94',   // Light mitti
  '255, 153, 51',   // Saffron
  '45, 74, 122',    // Neel (indigo accent)
];

interface GlobeParticlesProps {
  className?: string;
}

const GlobeParticles: React.FC<GlobeParticlesProps> = ({ className = '' }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animFrameRef = useRef<number>(0);
  const particleData = useRef<any>(null);
  const countRef = useRef(0);
  const mouseRef = useRef({ x: -9999, y: -9999 });
  const smoothMouseRef = useRef({ x: -9999, y: -9999 });

  const init = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;

    const area = canvas.width * canvas.height;
    const count = Math.min(Math.floor(area / 1200), 30000);
    countRef.current = count;
    const globeRadius = Math.max(canvas.width, canvas.height) * 0.4;

    const posX = new Float32Array(count);
    const posY = new Float32Array(count);
    const velX = new Float32Array(count);
    const velY = new Float32Array(count);
    const baseX = new Float32Array(count);
    const baseY = new Float32Array(count);
    const baseZ = new Float32Array(count);
    const sizes = new Float32Array(count);
    const colorIndices = new Uint8Array(count);
    const opacities = new Float32Array(count);

    for (let i = 0; i < count; i++) {
      const u = Math.random();
      const v = Math.random();
      const theta = 2 * Math.PI * u;
      const phi = Math.acos(2 * v - 1);
      const r = (Math.cbrt(Math.random()) * globeRadius * 0.8) + (globeRadius * 0.2);

      baseX[i] = r * Math.sin(phi) * Math.cos(theta);
      baseY[i] = r * Math.sin(phi) * Math.sin(theta);
      baseZ[i] = r * Math.cos(phi);
      sizes[i] = Math.random() * 2.5 + 1;
      colorIndices[i] = (Math.random() * COLORS.length) | 0;
      opacities[i] = Math.random() * 0.5 + 0.25;
    }

    particleData.current = {
      posX, posY, velX, velY,
      baseX, baseY, baseZ,
      sizes, colorIndices, opacities,
      dpr,
    };
  }, []);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || !particleData.current) return;
    const ctx = canvas.getContext('2d', { alpha: true });
    if (!ctx) return;
    const { width, height } = canvas;

    ctx.clearRect(0, 0, width, height);

    const m = mouseRef.current;
    const sm = smoothMouseRef.current;
    const { dpr } = particleData.current;

    if (m.x !== -9999) {
      if (sm.x === -9999) {
        sm.x = m.x * dpr;
        sm.y = m.y * dpr;
      } else {
        sm.x += (m.x * dpr - sm.x) * 0.3;
        sm.y += (m.y * dpr - sm.y) * 0.3;
      }
    } else {
      sm.x += (-9999 - sm.x) * 0.15;
    }

    const t = Date.now() * 0.0003;
    const cx = width / 2;
    const cy = height / 2;

    const count = countRef.current;
    const {
      posX, posY, velX, velY,
      baseX, baseY, baseZ,
      sizes, colorIndices, opacities,
    } = particleData.current;

    const repelRadius = 140 * dpr;
    const repelStrength = 90 * dpr;
    const repelRadiusSq = repelRadius * repelRadius;
    const fov = 800 * dpr;

    const sinX = Math.sin(t * 0.25);
    const cosX = Math.cos(t * 0.25);
    const sinY = Math.sin(t * 0.4);
    const cosY = Math.cos(t * 0.4);

    const mouseActive = sm.x > -1000;
    const numColors = COLORS.length;
    const colorOpacitySum = new Float64Array(numColors);
    const colorWidthSum = new Float64Array(numColors);
    const colorCountArr = new Uint32Array(numColors);
    const colorPathData = new Float32Array(count * 4);

    for (let i = 0; i < count; i++) {
      const bx = baseX[i];
      const by = baseY[i];
      const bz = baseZ[i];

      const rx = bx * cosY - bz * sinY;
      const rz1 = bx * sinY + bz * cosY;
      const ry = by * cosX - rz1 * sinX;
      const rz2 = by * sinX + rz1 * cosX;

      const scale = fov / (fov + rz2);

      let targetX = cx + rx * scale;
      let targetY = cy + ry * scale;

      if (mouseActive) {
        const dx = targetX - sm.x;
        const dy = targetY - sm.y;
        const distSq = dx * dx + dy * dy;

        if (distSq < repelRadiusSq && distSq > 0) {
          const dist = Math.sqrt(distSq);
          const force = (1 - dist / repelRadius);
          const push = force * force * repelStrength / dist;
          targetX += dx * push;
          targetY += dy * push;
        }
      }

      if (posX[i] === 0 && posY[i] === 0) {
        posX[i] = cx;
        posY[i] = cy;
      }

      velX[i] = (velX[i] + (targetX - posX[i]) * 0.1) * 0.84;
      velY[i] = (velY[i] + (targetY - posY[i]) * 0.1) * 0.84;
      posX[i] += velX[i];
      posY[i] += velY[i];

      const vxI = velX[i];
      const vyI = velY[i];
      const speed = Math.sqrt(vxI * vxI + vyI * vyI);
      const streakLength = Math.max(1.5, speed * 2);

      const zOpacity = Math.max(0.08, Math.min(1, (rz2 + 800) / 1600));
      const opacity = opacities[i] * zOpacity * scale;
      const lineWidth = Math.max(0.3, sizes[i] * scale * dpr * 0.7);

      let dirX: number, dirY: number;
      if (speed < 0.1) {
        const radX = posX[i] - cx;
        const radY = posY[i] - cy;
        const rd = Math.sqrt(radX * radX + radY * radY) || 1;
        dirX = radX / rd;
        dirY = radY / rd;
      } else {
        dirX = vxI / speed;
        dirY = vyI / speed;
      }

      const ci = colorIndices[i];
      const offset = i * 4;
      colorPathData[offset] = posX[i];
      colorPathData[offset + 1] = posY[i];
      colorPathData[offset + 2] = posX[i] - dirX * streakLength;
      colorPathData[offset + 3] = posY[i] - dirY * streakLength;

      colorOpacitySum[ci] += opacity;
      colorWidthSum[ci] += lineWidth;
      colorCountArr[ci]++;
    }

    ctx.lineCap = 'round';

    for (let c = 0; c < numColors; c++) {
      if (colorCountArr[c] === 0) continue;

      const avgOpacity = colorOpacitySum[c] / colorCountArr[c];
      const avgWidth = colorWidthSum[c] / colorCountArr[c];

      ctx.beginPath();
      for (let i = 0; i < count; i++) {
        if (colorIndices[i] !== c) continue;
        const offset = i * 4;
        ctx.moveTo(colorPathData[offset], colorPathData[offset + 1]);
        ctx.lineTo(colorPathData[offset + 2], colorPathData[offset + 3]);
      }

      ctx.strokeStyle = `rgba(${COLORS[c]}, ${avgOpacity})`;
      ctx.lineWidth = avgWidth;
      ctx.stroke();
    }

    animFrameRef.current = requestAnimationFrame(draw);
  }, []);

  useEffect(() => {
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduceMotion) return;

    init();
    animFrameRef.current = requestAnimationFrame(draw);

    const canvas = canvasRef.current;
    const parent = canvas?.parentElement;
    let cachedRect = canvas?.getBoundingClientRect();

    const handleMouseMove = (e: MouseEvent) => {
      if (!cachedRect) return;
      mouseRef.current = {
        x: e.clientX - cachedRect.left,
        y: e.clientY - cachedRect.top,
      };
    };

    const handleMouseLeave = () => {
      mouseRef.current = { x: -9999, y: -9999 };
    };

    let resizeTimer: ReturnType<typeof setTimeout>;
    const handleResize = () => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => {
        init();
        if (canvas) cachedRect = canvas.getBoundingClientRect();
      }, 200);
    };

    parent?.addEventListener('mousemove', handleMouseMove, { passive: true });
    parent?.addEventListener('mouseleave', handleMouseLeave);
    window.addEventListener('resize', handleResize, { passive: true });

    return () => {
      parent?.removeEventListener('mousemove', handleMouseMove);
      parent?.removeEventListener('mouseleave', handleMouseLeave);
      window.removeEventListener('resize', handleResize);
      clearTimeout(resizeTimer);
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, [init, draw]);

  return (
    <canvas
      ref={canvasRef}
      className={`pointer-events-none absolute inset-0 w-full h-full z-0 ${className}`}
      style={{ opacity: 1 }}
      aria-hidden="true"
    />
  );
};

export default GlobeParticles;
