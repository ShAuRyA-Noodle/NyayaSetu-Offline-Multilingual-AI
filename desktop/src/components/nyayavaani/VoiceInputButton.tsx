import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Mic, MicOff, Loader2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTranslation } from 'react-i18next';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001';

interface VoiceInputButtonProps {
  onTranscription: (text: string, language: string) => void;
  languageHint?: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

type RecordingState = 'idle' | 'recording' | 'processing';

const VoiceInputButton: React.FC<VoiceInputButtonProps> = ({
  onTranscription,
  languageHint,
  size = 'md',
  className = '',
}) => {
  const { t } = useTranslation();
  const [state, setState] = useState<RecordingState>('idle');
  const [duration, setDuration] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationRef = useRef<number | null>(null);

  const sizeClasses = {
    sm: 'w-10 h-10',
    md: 'w-14 h-14',
    lg: 'w-20 h-20',
  };

  const iconSizes = { sm: 18, md: 24, lg: 32 };

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
      if (mediaRecorderRef.current?.state === 'recording') {
        mediaRecorderRef.current.stop();
      }
    };
  }, []);

  const drawWaveform = useCallback(() => {
    const canvas = canvasRef.current;
    const analyser = analyserRef.current;
    if (!canvas || !analyser) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    analyser.getByteTimeDomainData(dataArray);

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.lineWidth = 2;
    ctx.strokeStyle = '#FF9933';
    ctx.beginPath();

    const sliceWidth = canvas.width / bufferLength;
    let x = 0;
    for (let i = 0; i < bufferLength; i++) {
      const v = dataArray[i] / 128.0;
      const y = (v * canvas.height) / 2;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
      x += sliceWidth;
    }
    ctx.lineTo(canvas.width, canvas.height / 2);
    ctx.stroke();

    animationRef.current = requestAnimationFrame(drawWaveform);
  }, []);

  const startRecording = async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      // Set up audio analyser for waveform
      const audioCtx = new AudioContext();
      const source = audioCtx.createMediaStreamSource(stream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      analyserRef.current = analyser;

      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/mp4',
      });
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        if (animationRef.current) cancelAnimationFrame(animationRef.current);

        const blob = new Blob(chunksRef.current, { type: mediaRecorder.mimeType });
        if (blob.size === 0) {
          setState('idle');
          setError('No audio recorded');
          return;
        }

        setState('processing');
        try {
          const formData = new FormData();
          formData.append('audio', blob, 'recording.webm');
          if (languageHint) formData.append('language_hint', languageHint);

          const response = await fetch(`${API_BASE_URL}/api/v1/nyayavaani/transcribe`, {
            method: 'POST',
            headers: {
              Authorization: `Bearer ${localStorage.getItem('token')}`,
            },
            body: formData,
          });

          if (!response.ok) throw new Error('Transcription failed');
          const data = await response.json();
          onTranscription(data.text, data.language);
        } catch (err) {
          console.error('Transcription error:', err);
          setError('Failed to transcribe audio');
        }
        setState('idle');
        setDuration(0);
      };

      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.start(250);
      setState('recording');

      // Timer
      setDuration(0);
      timerRef.current = setInterval(() => setDuration((d) => d + 1), 1000);

      // Start waveform
      drawWaveform();
    } catch (err) {
      console.error('Microphone access error:', err);
      setError('Microphone access denied');
    }
  };

  const stopRecording = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (mediaRecorderRef.current?.state === 'recording') {
      mediaRecorderRef.current.stop();
    }
  };

  const formatDuration = (s: number) => `${Math.floor(s / 60)}:${(s % 60).toString().padStart(2, '0')}`;

  return (
    <div className={`flex flex-col items-center gap-2 ${className}`}>
      <motion.button
        onClick={state === 'recording' ? stopRecording : startRecording}
        disabled={state === 'processing'}
        className={`${sizeClasses[size]} rounded-full flex items-center justify-center transition-all shadow-lg ${
          state === 'recording'
            ? 'bg-red-500 hover:bg-red-600 text-white shadow-red-500/30'
            : state === 'processing'
            ? 'bg-gray-400 cursor-not-allowed text-white'
            : 'bg-gradient-to-br from-saffron-500 to-orange-500 hover:from-saffron-600 hover:to-orange-600 text-white shadow-saffron'
        }`}
        whileTap={state !== 'processing' ? { scale: 0.9 } : undefined}
        animate={state === 'recording' ? { scale: [1, 1.1, 1] } : {}}
        transition={state === 'recording' ? { repeat: Infinity, duration: 1.5 } : {}}
      >
        {state === 'processing' ? (
          <Loader2 size={iconSizes[size]} className="animate-spin" />
        ) : state === 'recording' ? (
          <MicOff size={iconSizes[size]} />
        ) : (
          <Mic size={iconSizes[size]} />
        )}
      </motion.button>

      <AnimatePresence>
        {state === 'recording' && (
          <motion.div
            initial={{ opacity: 0, y: -5 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="flex flex-col items-center gap-1"
          >
            <canvas
              ref={canvasRef}
              width={120}
              height={30}
              className="rounded"
            />
            <span className="text-xs font-mono text-red-500">
              {formatDuration(duration)}
            </span>
            <span className="text-[10px] text-gray-500">
              {t('nyayavaani.stopRecording')}
            </span>
          </motion.div>
        )}
        {state === 'processing' && (
          <motion.span
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-xs text-saffron-600"
          >
            {t('nyayavaani.processing')}
          </motion.span>
        )}
        {state === 'idle' && !error && (
          <span className="text-[10px] text-gray-400">{t('nyayavaani.tapToSpeak')}</span>
        )}
      </AnimatePresence>

      {error && (
        <span className="text-xs text-red-500">{error}</span>
      )}
    </div>
  );
};

export default VoiceInputButton;
