import React, { useEffect, useState, useRef, useCallback } from 'react';

interface TypewriterTextProps {
  text: string;
  speed?: number;
  className?: string;
  showCursor?: boolean;
  onComplete?: () => void;
  startDelay?: number;
}

const TypewriterText: React.FC<TypewriterTextProps> = ({
  text,
  speed = 30,
  className = '',
  showCursor = true,
  onComplete,
  startDelay = 0,
}) => {
  const [displayedText, setDisplayedText] = useState('');
  const [isComplete, setIsComplete] = useState(false);
  const [isSkipped, setIsSkipped] = useState(false);
  const indexRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout>>();

  const reduceMotion = typeof window !== 'undefined'
    ? window.matchMedia('(prefers-reduced-motion: reduce)').matches
    : false;

  // Allow clicking to skip / reveal all
  const handleSkip = useCallback(() => {
    if (isComplete) return;
    setIsSkipped(true);
    setDisplayedText(text);
    setIsComplete(true);
    if (timerRef.current) clearTimeout(timerRef.current);
    onComplete?.();
  }, [text, isComplete, onComplete]);

  useEffect(() => {
    if (reduceMotion) {
      setDisplayedText(text);
      setIsComplete(true);
      onComplete?.();
      return;
    }

    if (isSkipped) return;

    indexRef.current = 0;
    setDisplayedText('');
    setIsComplete(false);

    const startTyping = () => {
      const type = () => {
        if (indexRef.current < text.length) {
          setDisplayedText(text.slice(0, indexRef.current + 1));
          indexRef.current++;

          // Variable speed: pause longer at punctuation
          const char = text[indexRef.current - 1];
          const delay = '.!?'.includes(char) ? speed * 6 :
                        ',;:'.includes(char) ? speed * 3 :
                        ' '.includes(char) ? speed * 0.5 :
                        speed;

          timerRef.current = setTimeout(type, delay);
        } else {
          setIsComplete(true);
          onComplete?.();
        }
      };
      type();
    };

    if (startDelay > 0) {
      timerRef.current = setTimeout(startTyping, startDelay);
    } else {
      startTyping();
    }

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [text, speed, startDelay, reduceMotion, isSkipped, onComplete]);

  return (
    <span
      className={`${className} ${!isComplete && showCursor ? 'typewriter-cursor' : ''}`}
      onClick={handleSkip}
      role="text"
      aria-label={text}
      style={{ cursor: isComplete ? 'default' : 'pointer' }}
    >
      {displayedText}
    </span>
  );
};

export default TypewriterText;
