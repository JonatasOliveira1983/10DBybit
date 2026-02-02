
import React, { useEffect } from 'react';
import { motion, useAnimation } from 'framer-motion';

interface Props {
  progress: number;
}

/**
 * ICLogoLoader: Versão de alta fidelidade baseada na imagem de referência.
 * Ajustes:
 * - 'C' reduzido para proporção correta.
 * - Faixa externa (track) com espessura aumentada para destaque neon.
 * - Barras verticais mais finas e precisas.
 * - Cores e brilhos sincronizados com o gradiente da imagem.
 */
const ICLogoLoader: React.FC<Props> = ({ progress }) => {
  const controls = useAnimation();

  // Efeito de ativação final ao atingir 98%
  useEffect(() => {
    if (progress >= 98) {
      controls.start({
        scale: [1, 1.03, 1],
        filter: [
          'drop-shadow(0 0 12px rgba(0,255,255,0.3))',
          'drop-shadow(0 0 35px rgba(112,0,255,0.6))',
          'drop-shadow(0 0 12px rgba(0,255,255,0.3))'
        ],
        transition: { duration: 0.8, ease: "easeInOut" }
      });
    }
  }, [progress, controls]);

  return (
    <motion.div 
      className="relative flex items-center justify-center"
      animate={controls}
    >
      {/* Brilho de fundo atmosférico */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        <motion.div 
          animate={{ 
            opacity: [0.06, 0.14, 0.06],
            scale: [0.9, 1.1, 0.9]
          }}
          transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
          className="w-[450px] h-[450px] bg-[#7000FF]/10 blur-[140px] rounded-full"
        />
      </div>

      <svg 
        width="380" 
        height="380" 
        viewBox="0 0 280 280" 
        fill="none" 
        xmlns="http://www.w3.org/2000/svg"
        className="relative z-10"
      >
        <defs>
          {/* Gradiente Fiel: Magenta -> Roxo -> Ciano */}
          <linearGradient id="logoNeonGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#FF00FF" />
            <stop offset="50%" stopColor="#7000FF" />
            <stop offset="100%" stopColor="#00FFFF" />
          </linearGradient>

          {/* Filtro de Bloom (Brilho Intenso) */}
          <filter id="bloomFilter" x="-100%" y="-100%" width="300%" height="300%">
            <feGaussianBlur stdDeviation="5" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>

          {/* Filtro de Brilho Suave para a faixa externa */}
          <filter id="softGlow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="2.5" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        {/* 1. AS BARRAS VERTICAIS "II" - Finas e elegantes como na imagem */}
        <g transform="translate(65, 140)">
          {/* Barra Esquerda (Mais alta) */}
          <motion.rect
            x="0"
            y="-75"
            width="6"
            height="150"
            rx="1.2"
            fill="url(#logoNeonGradient)"
            initial={{ scaleY: 0, opacity: 0, y: 25 }}
            animate={{ scaleY: 1, opacity: 1, y: 0 }}
            transition={{ 
              duration: 1.2, 
              ease: [0.19, 1, 0.22, 1],
              delay: 0.1 
            }}
            style={{ originY: 1, filter: 'url(#bloomFilter)' }}
          />

          {/* Barra Direita (Menor) */}
          <motion.rect
            x="18"
            y="-52"
            width="6"
            height="130"
            rx="1.2"
            fill="url(#logoNeonGradient)"
            initial={{ scaleY: 0, opacity: 0, y: 25 }}
            animate={{ scaleY: 1, opacity: 1, y: 0 }}
            transition={{ 
              duration: 1, 
              ease: [0.19, 1, 0.22, 1],
              delay: 0.25 
            }}
            style={{ originY: 1, filter: 'url(#bloomFilter)' }}
          />
        </g>

        {/* 2. O CONJUNTO "C" - Redimensionado e com espessuras calibradas */}
        <g transform="translate(180, 140)">
          
          {/* FAIXA EXTERNA (TRACK) - Mais grossa que o detalhe interno, com pulso */}
          <motion.path
            d="M 40 -68 A 78 78 0 1 0 40 68"
            stroke="url(#logoNeonGradient)"
            strokeWidth="5" 
            fill="transparent"
            initial={{ pathLength: 0, opacity: 0 }}
            animate={{ 
              pathLength: progress > 15 ? (progress - 15) / 85 : 0,
              opacity: progress > 10 ? [0.4, 0.7, 0.4] : 0
            }}
            transition={{ 
              pathLength: { duration: 0.8, ease: "easeOut" },
              opacity: { duration: 3, repeat: Infinity, ease: "easeInOut" }
            }}
            style={{ filter: 'url(#softGlow)' }}
          />

          {/* CORPO PRINCIPAL DO "C" - Robusto e central */}
          <motion.path
            d="M 32 -54 A 62 62 0 1 0 32 54"
            stroke="url(#logoNeonGradient)"
            strokeWidth="26"
            strokeLinecap="round"
            fill="transparent"
            initial={{ pathLength: 0, opacity: 0 }}
            animate={{ 
              pathLength: progress / 100,
              opacity: progress > 5 ? 1 : 0
            }}
            transition={{ duration: 0.6, ease: "linear" }}
            style={{ filter: 'url(#bloomFilter)' }}
          />

          {/* DETALHE INTERNO (REFLEXO) - Mais fino que a faixa externa */}
          <motion.path
            d="M 28 -48 A 56 56 0 1 0 28 48"
            stroke="white"
            strokeWidth="1.5"
            strokeOpacity="0.15"
            strokeLinecap="round"
            fill="transparent"
            initial={{ pathLength: 0 }}
            animate={{ pathLength: progress / 100 }}
            transition={{ duration: 0.6, ease: "linear" }}
          />
        </g>

        {/* Partículas de Dados - Profundidade e tecnologia */}
        {[...Array(8)].map((_, i) => (
          <motion.circle
            key={i}
            r={0.6 + Math.random()}
            fill="white"
            initial={{ opacity: 0 }}
            animate={{ 
              opacity: [0, 0.4, 0],
              x: [140, 140 + (i - 4) * 35],
              y: [140, 140 + (Math.random() - 0.5) * 160],
            }}
            transition={{ 
              duration: 4 + Math.random() * 4, 
              repeat: Infinity, 
              delay: i * 0.6 
            }}
          />
        ))}
      </svg>
    </motion.div>
  );
};

export default ICLogoLoader;
