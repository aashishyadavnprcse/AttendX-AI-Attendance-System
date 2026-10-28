/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ['class'],
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './src/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        background: {
          DEFAULT: '#0B0F19',
          darker: '#060911',
          lighter: '#101726',
        },
        surface: {
          DEFAULT: '#111827',
          elevated: '#172236',
          translucent: 'rgba(17, 24, 39, 0.65)',
          border: 'rgba(255, 255, 255, 0.08)',
          'border-focus': 'rgba(6, 182, 212, 0.5)',
        },
        brand: {
          cyan: {
            DEFAULT: '#06B6D4', // Primary Accent
            glow: '#22D3EE',
            dim: '#0891B2',
            subtle: 'rgba(6, 182, 212, 0.12)',
            surface: 'rgba(6, 182, 212, 0.05)',
          },
          emerald: {
            DEFAULT: '#10B981', // Present / Success
            glow: '#34D399',
            dim: '#059669',
            subtle: 'rgba(16, 185, 129, 0.12)',
          },
          rose: {
            DEFAULT: '#F43F5E', // Spoof / Danger / Absent
            glow: '#FB7185',
            dim: '#E11D48',
            subtle: 'rgba(244, 63, 94, 0.12)',
          },
          amber: {
            DEFAULT: '#F59E0B', // Anomaly / Warning
            glow: '#FBBF24',
            subtle: 'rgba(245, 158, 11, 0.12)',
          },
          violet: {
            DEFAULT: '#8B5CF6', // AI Vision / Analytics
            glow: '#A78BFA',
            subtle: 'rgba(139, 92, 246, 0.12)',
          },
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      boxShadow: {
        'glow-cyan-sm': '0 0 10px -2px rgba(6, 182, 212, 0.4)',
        'glow-cyan': '0 0 20px -3px rgba(6, 182, 212, 0.45), 0 0 8px -2px rgba(6, 182, 212, 0.3)',
        'glow-cyan-lg': '0 0 35px -5px rgba(6, 182, 212, 0.6), 0 0 15px -3px rgba(6, 182, 212, 0.4)',
        'glow-emerald': '0 0 20px -3px rgba(16, 185, 129, 0.45), 0 0 8px -2px rgba(16, 185, 129, 0.3)',
        'glow-rose': '0 0 20px -3px rgba(244, 63, 94, 0.45), 0 0 8px -2px rgba(244, 63, 94, 0.3)',
        'glow-amber': '0 0 20px -3px rgba(245, 158, 11, 0.45), 0 0 8px -2px rgba(245, 158, 11, 0.3)',
        'glass-card': '0 8px 32px 0 rgba(0, 0, 0, 0.45)',
        'glass-inset': 'inset 0 1px 1px 0 rgba(255, 255, 255, 0.1)',
      },
      backgroundImage: {
        'cyber-gradient': 'radial-gradient(ellipse 80% 50% at 50% -20%, rgba(6, 182, 212, 0.18), transparent 70%)',
        'mesh-glow': 'radial-gradient(circle at 10% 20%, rgba(6, 182, 212, 0.12) 0%, transparent 40%), radial-gradient(circle at 90% 80%, rgba(139, 92, 246, 0.1) 0%, transparent 40%)',
        'glass-gradient': 'linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0.01) 100%)',
      },
      animation: {
        'pulse-glow': 'pulseGlow 2.5s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'radar-sweep': 'radarSweep 3s linear infinite',
        'scan-line': 'scanLine 2.2s ease-in-out infinite',
        'beacon': 'beacon 1.8s cubic-bezier(0, 0, 0.2, 1) infinite',
        'float-slow': 'float 6s ease-in-out infinite',
      },
      keyframes: {
        pulseGlow: {
          '0%, 100%': { opacity: '0.4', transform: 'scale(1)' },
          '50%': { opacity: '0.8', transform: 'scale(1.02)' },
        },
        radarSweep: {
          '0%': { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(360deg)' },
        },
        scanLine: {
          '0%': { top: '0%', opacity: '0' },
          '15%': { opacity: '1' },
          '85%': { opacity: '1' },
          '100%': { top: '100%', opacity: '0' },
        },
        beacon: {
          '0%': { transform: 'scale(0.95)', opacity: '1' },
          '70%, 100%': { transform: 'scale(2.2)', opacity: '0' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-6px)' },
        },
      },
      backdropBlur: {
        'xs': '2px',
        '2xl': '24px',
        '3xl': '40px',
      },
    },
  },
  plugins: [],
}
