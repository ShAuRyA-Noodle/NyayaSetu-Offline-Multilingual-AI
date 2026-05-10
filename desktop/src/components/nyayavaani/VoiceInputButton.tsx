import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Mic, Square, Loader2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import apiService from '../../services/api';

interface VoiceInputButtonProps {
  onTranscription: (text: string, language: string) => void;
  languageHint?: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  label?: string;
}

type RecordingState = 'idle' | 'recording' | 'processing';

// Animated bars component for recording visualization
const AudioBars: React.FC<{ analyser: AnalyserNode | null; barCount?: number }> = ({ analyser, barCount = 24 }) => {
  const barsRef = useRef<HTMLDivElement>(null);
  const rafRef = useRef<number>(0);
  const dataArray = useRef<Uint8Array<ArrayBuffer> | null>(null);

  useEffect(() => {
    if (!analyser) return;
    dataArray.current = new Uint8Array(analyser.frequencyBinCount);

    const draw = () => {
      if (!analyser || !barsRef.current || !dataArray.current) return;
      analyser.getByteFrequencyData(dataArray.current);

      const bars = barsRef.current.children;
      const step = Math.floor(dataArray.current.length / barCount);
      for (let i = 0; i < barCount && i < bars.length; i++) {
        const val = dataArray.current[i * step] / 255;
        const height = Math.max(4, val * 32);
        (bars[i] as HTMLElement).style.height = `${height}px`;
        (bars[i] as HTMLElement).style.opacity = `${0.4 + val * 0.6}`;
      }
      rafRef.current = requestAnimationFrame(draw);
    };

    draw();
    return () => cancelAnimationFrame(rafRef.current);
  }, [analyser, barCount]);

  return (
    <div ref={barsRef} className="flex items-center justify-center gap-[2px] h-8">
      {Array.from({ length: barCount }).map((_, i) => (
        <div
          key={i}
          className="w-[3px] rounded-full bg-[#0D92F4] transition-all"
          style={{
            height: '4px',
            opacity: 0.3,
            transitionDuration: '50ms',
          }}
        />
      ))}
    </div>
  );
};

const VoiceInputButton: React.FC<VoiceInputButtonProps> = ({
  onTranscription,
  languageHint,
  size = 'md',
  className = '',
  label,
}) => {
  const [state, setState] = useState<RecordingState>('idle');
  const [duration, setDuration] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [analyser, setAnalyser] = useState<AnalyserNode | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);

  const sizeMap = { sm: 40, md: 48, lg: 56 };
  const iconMap = { sm: 16, md: 20, lg: 24 };
  const btnSize = sizeMap[size];
  const iconSize = iconMap[size];

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (mediaRecorderRef.current?.state === 'recording') mediaRecorderRef.current.stop();
      audioCtxRef.current?.close();
    };
  }, []);

  const startRecording = async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, sampleRate: 16000 },
      });

      const audioCtx = new AudioContext();
      audioCtxRef.current = audioCtx;
      const source = audioCtx.createMediaStreamSource(stream);
      const node = audioCtx.createAnalyser();
      node.fftSize = 128;
      node.smoothingTimeConstant = 0.8;
      source.connect(node);
      setAnalyser(node);

      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
          ? 'audio/webm;codecs=opus'
          : MediaRecorder.isTypeSupported('audio/webm')
          ? 'audio/webm'
          : 'audio/mp4',
      });
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        setAnalyser(null);
        audioCtx.close();

        const blob = new Blob(chunksRef.current, { type: mediaRecorder.mimeType });
        if (blob.size === 0) {
          setState('idle');
          setError('No audio captured');
          return;
        }

        setState('processing');
        try {
          const fd = new FormData();
          fd.append('audio', blob, 'recording.webm');
          if (languageHint) fd.append('language_hint', languageHint);

          const data = await apiService.transcribeAudio(fd);
          if (data?.text?.trim()) {
            onTranscription(data.text.trim(), data.language || 'auto');
          } else {
            setError('Could not detect speech. Try again.');
          }
        } catch (err: any) {
          console.error('Transcription error:', err);
          const detail = err?.response?.data?.detail;
          setError(
            (typeof detail === 'string' ? detail : null) ||
              err?.message ||
              'Transcription failed'
          );
        }
        setState('idle');
        setDuration(0);
      };

      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.start(250);
      setState('recording');
      setDuration(0);
      timerRef.current = setInterval(() => setDuration((d) => d + 1), 1000);
    } catch (err: any) {
      console.error('Mic error:', err);
      setError(err.name === 'NotAllowedError' ? 'Microphone access denied. Please allow mic access.' : 'Microphone unavailable');
    }
  };

  const stopRecording = useCallback(() => {
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
    if (mediaRecorderRef.current?.state === 'recording') mediaRecorderRef.current.stop();
  }, []);

  // Auto-stop at 60 seconds
  useEffect(() => {
    if (state === 'recording' && duration >= 60) stopRecording();
  }, [state, duration, stopRecording]);

  const fmt = (s: number) => `${Math.floor(s / 60)}:${(s % 60).toString().padStart(2, '0')}`;

  const isRecording = state === 'recording';
  const isProcessing = state === 'processing';

  return (
    <div className={`flex flex-col items-center ${className}`}>
      {/* Main button */}
      <div className="relative">
        {/* Pulse rings when recording */}
        <AnimatePresence>
          {isRecording && (
            <>
              <motion.div
                className="absolute inset-0 rounded-full border-2 border-[#F95454]/30"
                initial={{ scale: 1, opacity: 0.6 }}
                animate={{ scale: 2.2, opacity: 0 }}
                transition={{ duration: 1.5, repeat: Infinity, ease: 'easeOut' }}
              />
              <motion.div
                className="absolute inset-0 rounded-full border border-[#F95454]/20"
                initial={{ scale: 1, opacity: 0.4 }}
                animate={{ scale: 1.8, opacity: 0 }}
                transition={{ duration: 1.5, repeat: Infinity, ease: 'easeOut', delay: 0.3 }}
              />
            </>
          )}
        </AnimatePresence>

        <motion.button
          onClick={isRecording ? stopRecording : startRecording}
          disabled={isProcessing}
          className={`relative z-10 rounded-full flex items-center justify-center transition-all ${
            isRecording
              ? 'bg-[#F95454] shadow-lg shadow-[#F95454]/30 hover:bg-[#E04040]'
              : isProcessing
              ? 'bg-slate-600 cursor-wait'
              : 'bg-gradient-to-br from-[#0D92F4] to-[#0B7DD4] shadow-lg shadow-[#0D92F4]/20 hover:shadow-[#0D92F4]/40 hover:scale-105'
          }`}
          style={{ width: btnSize, height: btnSize }}
          whileTap={!isProcessing ? { scale: 0.9 } : undefined}
          transition={{ type: 'spring', stiffness: 400, damping: 15 }}
        >
          {isProcessing ? (
            <Loader2 size={iconSize} className="text-white animate-spin" />
          ) : isRecording ? (
            <Square size={iconSize - 4} className="text-white" fill="white" />
          ) : (
            <Mic size={iconSize} className="text-white" />
          )}
        </motion.button>
      </div>

      {/* Recording state UI */}
      <AnimatePresence mode="wait">
        {isRecording && (
          <motion.div
            key="recording"
            initial={{ opacity: 0, y: -8, height: 0 }}
            animate={{ opacity: 1, y: 0, height: 'auto' }}
            exit={{ opacity: 0, y: -8, height: 0 }}
            transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
            className="flex flex-col items-center gap-2 mt-3 overflow-hidden"
          >
            <AudioBars analyser={analyser} barCount={size === 'sm' ? 16 : 24} />
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-[#F95454] animate-pulse" />
              <span className="text-xs font-mono text-[#F95454] tabular-nums">{fmt(duration)}</span>
            </div>
            <span className="text-[10px] text-slate-500">Tap to stop · Max 60s</span>
          </motion.div>
        )}

        {isProcessing && (
          <motion.div
            key="processing"
            initial={{ opacity: 0, y: -5 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="mt-3 flex items-center gap-2"
          >
            <div className="flex gap-1">
              {[0, 1, 2].map((i) => (
                <motion.div key={i} className="w-1.5 h-1.5 rounded-full bg-[#0D92F4]"
                  animate={{ opacity: [0.3, 1, 0.3] }}
                  transition={{ duration: 1, repeat: Infinity, delay: i * 0.15 }}
                />
              ))}
            </div>
            <span className="text-xs text-[#77CDFF]">Transcribing...</span>
          </motion.div>
        )}

        {state === 'idle' && !error && (
          <motion.span
            key="idle"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mt-2 text-[10px] text-slate-500"
          >
            {label || 'Tap to speak'}
          </motion.span>
        )}
      </AnimatePresence>

      {/* Error */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -5 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="mt-2 px-3 py-1.5 rounded-lg bg-[#F95454]/10 border border-[#F95454]/20"
          >
            <span className="text-[11px] text-[#F95454]">{error}</span>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default VoiceInputButton;
