import { useMemo } from 'react';

type TimeOfDay = 'morning' | 'afternoon' | 'evening' | 'night';

interface TimeOfDayConfig {
  period: TimeOfDay;
  greeting: string;
  greetingHindi: string;
  ambientHue: number; // HSL hue for ambient color shift
  ambientSaturation: number;
}

const TIME_CONFIG: Record<TimeOfDay, Omit<TimeOfDayConfig, 'period'>> = {
  morning: {
    greeting: 'Good Morning',
    greetingHindi: 'शुभ प्रभात',
    ambientHue: 35,       // warm amber
    ambientSaturation: 40,
  },
  afternoon: {
    greeting: 'Good Afternoon',
    greetingHindi: 'शुभ दोपहर',
    ambientHue: 30,       // golden
    ambientSaturation: 35,
  },
  evening: {
    greeting: 'Good Evening',
    greetingHindi: 'शुभ संध्या',
    ambientHue: 25,       // warm amber-orange
    ambientSaturation: 45,
  },
  night: {
    greeting: 'Good Night',
    greetingHindi: 'शुभ रात्रि',
    ambientHue: 220,      // cool blue
    ambientSaturation: 20,
  },
};

function getTimeOfDay(): TimeOfDay {
  const hour = new Date().getHours();
  if (hour >= 5 && hour < 12) return 'morning';
  if (hour >= 12 && hour < 17) return 'afternoon';
  if (hour >= 17 && hour < 21) return 'evening';
  return 'night';
}

export function useTimeOfDay(): TimeOfDayConfig {
  // Memoize based on the current period (recalculates on each render but stable within same period)
  const period = getTimeOfDay();

  return useMemo(() => ({
    period,
    ...TIME_CONFIG[period],
  }), [period]);
}

export default useTimeOfDay;
