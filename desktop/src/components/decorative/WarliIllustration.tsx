import React from 'react';

type WarliVariant = 'village' | 'farmer' | 'panchayat' | 'tree' | 'dance' | 'field';

interface WarliIllustrationProps {
  variant?: WarliVariant;
  size?: number;
  className?: string;
  color?: string;
}

const WarliIllustration: React.FC<WarliIllustrationProps> = ({
  variant = 'village',
  size = 200,
  className = '',
  color = '#C27B3A',
}) => {
  const opacity = 0.6;

  const illustrations: Record<WarliVariant, React.ReactNode> = {
    village: (
      // Village scene: huts + tree + people
      <g opacity={opacity}>
        {/* Hut 1 */}
        <polygon points="30,85 50,60 70,85" fill="none" stroke={color} strokeWidth="1.5" />
        <rect x="38" y="75" width="6" height="10" fill="none" stroke={color} strokeWidth="1" />
        {/* Hut 2 */}
        <polygon points="75,85 90,65 105,85" fill="none" stroke={color} strokeWidth="1.5" />
        <rect x="85" y="77" width="5" height="8" fill="none" stroke={color} strokeWidth="1" />
        {/* Tree */}
        <line x1="120" y1="85" x2="120" y2="55" stroke={color} strokeWidth="1.5" />
        <circle cx="120" cy="48" r="12" fill="none" stroke={color} strokeWidth="1" />
        <circle cx="113" cy="52" r="8" fill="none" stroke={color} strokeWidth="0.8" />
        <circle cx="127" cy="52" r="8" fill="none" stroke={color} strokeWidth="0.8" />
        {/* Person 1 — stick figure */}
        <circle cx="55" cy="50" r="3" fill={color} />
        <line x1="55" y1="53" x2="55" y2="65" stroke={color} strokeWidth="1.2" />
        <line x1="55" y1="57" x2="50" y2="62" stroke={color} strokeWidth="1" />
        <line x1="55" y1="57" x2="60" y2="62" stroke={color} strokeWidth="1" />
        <line x1="55" y1="65" x2="51" y2="73" stroke={color} strokeWidth="1" />
        <line x1="55" y1="65" x2="59" y2="73" stroke={color} strokeWidth="1" />
        {/* Ground line */}
        <line x1="10" y1="86" x2="140" y2="86" stroke={color} strokeWidth="0.5" strokeDasharray="3,3" />
      </g>
    ),
    farmer: (
      // Farmer with plow and ox
      <g opacity={opacity}>
        {/* Farmer */}
        <circle cx="60" cy="35" r="4" fill={color} />
        <line x1="60" y1="39" x2="60" y2="55" stroke={color} strokeWidth="1.5" />
        <line x1="60" y1="44" x2="54" y2="50" stroke={color} strokeWidth="1.2" />
        <line x1="60" y1="44" x2="68" y2="48" stroke={color} strokeWidth="1.2" />
        <line x1="60" y1="55" x2="55" y2="65" stroke={color} strokeWidth="1.2" />
        <line x1="60" y1="55" x2="65" y2="65" stroke={color} strokeWidth="1.2" />
        {/* Plow handle */}
        <line x1="68" y1="48" x2="85" y2="55" stroke={color} strokeWidth="1" />
        <line x1="85" y1="55" x2="90" y2="68" stroke={color} strokeWidth="1" />
        {/* Ox */}
        <ellipse cx="105" cy="52" rx="12" ry="8" fill="none" stroke={color} strokeWidth="1.5" />
        <circle cx="115" cy="48" r="4" fill="none" stroke={color} strokeWidth="1.2" />
        <line x1="119" y1="47" x2="123" y2="44" stroke={color} strokeWidth="1" />
        <line x1="119" y1="49" x2="123" y2="46" stroke={color} strokeWidth="1" />
        {/* Ox legs */}
        <line x1="98" y1="60" x2="96" y2="70" stroke={color} strokeWidth="1" />
        <line x1="102" y1="60" x2="100" y2="70" stroke={color} strokeWidth="1" />
        <line x1="108" y1="60" x2="110" y2="70" stroke={color} strokeWidth="1" />
        <line x1="112" y1="60" x2="114" y2="70" stroke={color} strokeWidth="1" />
        {/* Ground */}
        <line x1="20" y1="70" x2="130" y2="70" stroke={color} strokeWidth="0.5" strokeDasharray="2,4" />
        {/* Field rows */}
        <path d="M20,75 Q50,72 80,75 Q110,78 130,75" fill="none" stroke={color} strokeWidth="0.5" />
        <path d="M20,80 Q50,77 80,80 Q110,83 130,80" fill="none" stroke={color} strokeWidth="0.5" />
      </g>
    ),
    panchayat: (
      // People sitting in circle — village council meeting
      <g opacity={opacity}>
        {/* Central circle (gathering space) */}
        <circle cx="75" cy="55" r="30" fill="none" stroke={color} strokeWidth="0.5" strokeDasharray="4,4" />
        {/* People around the circle */}
        {[0, 45, 90, 135, 180, 225, 270, 315].map((angle, i) => {
          const rad = (angle * Math.PI) / 180;
          const x = 75 + 30 * Math.cos(rad);
          const y = 55 + 30 * Math.sin(rad);
          return (
            <g key={i}>
              <circle cx={x} cy={y - 5} r="3" fill={color} />
              <line x1={x} y1={y - 2} x2={x} y2={y + 8} stroke={color} strokeWidth="1.2" />
              <line x1={x} y1={y + 2} x2={x - 4} y2={y + 6} stroke={color} strokeWidth="0.8" />
              <line x1={x} y1={y + 2} x2={x + 4} y2={y + 6} stroke={color} strokeWidth="0.8" />
            </g>
          );
        })}
        {/* Central fire/lamp */}
        <polygon points="75,50 72,56 78,56" fill={color} opacity="0.4" />
        <circle cx="75" cy="48" r="2" fill={color} opacity="0.3" />
      </g>
    ),
    tree: (
      // Banyan tree
      <g opacity={opacity}>
        <line x1="75" y1="90" x2="75" y2="45" stroke={color} strokeWidth="2.5" />
        {/* Main canopy */}
        <circle cx="75" cy="35" r="25" fill="none" stroke={color} strokeWidth="1.5" />
        <circle cx="60" cy="42" r="15" fill="none" stroke={color} strokeWidth="1" />
        <circle cx="90" cy="42" r="15" fill="none" stroke={color} strokeWidth="1" />
        <circle cx="75" cy="25" r="12" fill="none" stroke={color} strokeWidth="1" />
        {/* Aerial roots */}
        <line x1="60" y1="55" x2="58" y2="90" stroke={color} strokeWidth="0.8" />
        <line x1="90" y1="55" x2="92" y2="90" stroke={color} strokeWidth="0.8" />
        <line x1="68" y1="50" x2="66" y2="75" stroke={color} strokeWidth="0.6" />
        <line x1="82" y1="50" x2="84" y2="75" stroke={color} strokeWidth="0.6" />
        {/* Root base */}
        <path d="M50,90 Q75,85 100,90" fill="none" stroke={color} strokeWidth="0.8" />
      </g>
    ),
    dance: (
      // Warli dance circle
      <g opacity={opacity}>
        {[0, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330].map((angle, i) => {
          const rad = (angle * Math.PI) / 180;
          const x = 75 + 32 * Math.cos(rad);
          const y = 55 + 32 * Math.sin(rad);
          const armAngle = rad + (i % 2 === 0 ? 0.5 : -0.5);
          return (
            <g key={i}>
              <circle cx={x} cy={y - 4} r="2.5" fill={color} />
              <line x1={x} y1={y - 1.5} x2={x} y2={y + 7} stroke={color} strokeWidth="1" />
              <line x1={x} y1={y + 2} x2={x + 5 * Math.cos(armAngle)} y2={y + 2 + 5 * Math.sin(armAngle)} stroke={color} strokeWidth="0.8" />
              <line x1={x} y1={y + 2} x2={x - 5 * Math.cos(armAngle)} y2={y + 2 - 5 * Math.sin(armAngle)} stroke={color} strokeWidth="0.8" />
              <line x1={x} y1={y + 7} x2={x - 3} y2={y + 13} stroke={color} strokeWidth="0.8" />
              <line x1={x} y1={y + 7} x2={x + 3} y2={y + 13} stroke={color} strokeWidth="0.8" />
            </g>
          );
        })}
      </g>
    ),
    field: (
      // Agricultural field with rows
      <g opacity={opacity}>
        {/* Field rows */}
        {[0, 1, 2, 3, 4, 5].map(i => (
          <path
            key={i}
            d={`M15,${35 + i * 10} Q50,${30 + i * 10} 85,${35 + i * 10} Q120,${40 + i * 10} 140,${35 + i * 10}`}
            fill="none"
            stroke={color}
            strokeWidth="0.6"
          />
        ))}
        {/* Plants */}
        {[30, 55, 80, 105, 130].map((x, i) => (
          <g key={i}>
            <line x1={x} y1={40 + (i % 2) * 5} x2={x} y2={30 + (i % 2) * 5} stroke={color} strokeWidth="0.8" />
            <line x1={x} y1={34 + (i % 2) * 5} x2={x - 3} y2={30 + (i % 2) * 5} stroke={color} strokeWidth="0.6" />
            <line x1={x} y1={34 + (i % 2) * 5} x2={x + 3} y2={30 + (i % 2) * 5} stroke={color} strokeWidth="0.6" />
          </g>
        ))}
        {/* Sun */}
        <circle cx="130" cy="15" r="6" fill="none" stroke={color} strokeWidth="0.8" />
        {[0, 45, 90, 135, 180, 225, 270, 315].map(angle => {
          const rad = (angle * Math.PI) / 180;
          return (
            <line
              key={angle}
              x1={130 + 8 * Math.cos(rad)}
              y1={15 + 8 * Math.sin(rad)}
              x2={130 + 11 * Math.cos(rad)}
              y2={15 + 11 * Math.sin(rad)}
              stroke={color}
              strokeWidth="0.6"
            />
          );
        })}
      </g>
    ),
  };

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 150 100"
      className={`pointer-events-none ${className}`}
      preserveAspectRatio="xMidYMid meet"
    >
      {illustrations[variant]}
    </svg>
  );
};

export default WarliIllustration;
