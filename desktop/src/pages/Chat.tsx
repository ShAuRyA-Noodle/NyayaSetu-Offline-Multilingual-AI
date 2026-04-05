import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { Send, Bot, User, Loader2, Sparkles } from 'lucide-react';
import apiService from '../services/api';
import PageTransition from '../components/ui/PageTransition';
import VoiceInputButton from '../components/nyayavaani/VoiceInputButton';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  loading?: boolean;
}

const Chat: React.FC = () => {
  const { t, i18n } = useTranslation();
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1', role: 'assistant',
      content: 'Hello! I\'m your NyayaSetu assistant. Ask me anything about government schemes like PM-KISAN, MGNREGA, or PMAY-G. I can help you understand eligibility, benefits, and application processes.',
      timestamp: new Date(),
    }
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const language = (i18n.language || 'en') as 'en' | 'hi';
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  const handleSend = async () => {
    if (!input.trim()) return;
    const userMessage: Message = { id: Date.now().toString(), role: 'user', content: input, timestamp: new Date() };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsTyping(true);
    const loadingMessage: Message = { id: 'loading', role: 'assistant', content: '', timestamp: new Date(), loading: true };
    setMessages(prev => [...prev, loadingMessage]);
    try {
      const response = await apiService.askQuestion(input, language);
      setMessages(prev => prev.filter(msg => msg.id !== 'loading'));
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(), role: 'assistant',
        content: response.answer || 'I couldn\'t find a relevant answer. Could you rephrase?',
        timestamp: new Date(),
      }]);
    } catch {
      setMessages(prev => prev.filter(msg => msg.id !== 'loading'));
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(), role: 'assistant',
        content: 'Sorry, I encountered an error. Please check the backend and try again.',
        timestamp: new Date(),
      }]);
    } finally { setIsTyping(false); }
  };

  const suggestedQuestions = language === 'hi'
    ? ['PM-KISAN योजना क्या है?', 'MGNREGA के लिए पात्रता?', 'PMAY-G के लिए आवेदन कैसे करें?', 'PM-KISAN के लाभ क्या हैं?']
    : ['What is PM-KISAN scheme?', 'Am I eligible for MGNREGA?', 'How to apply for PMAY-G?', 'What are the benefits of PM-KISAN?'];

  return (
    <PageTransition className="flex flex-col h-[calc(100vh-4rem)]">
      {/* Header */}
      <div className="village-card border-b border-mitti-200/20 dark:border-night-border/40 px-4 md:px-6 py-4">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-gradient-to-br from-mitti-500 to-mitti-600 rounded-xl shadow-mitti">
            <Bot className="w-6 h-6 text-white" />
          </div>
          <div>
            <h2 className="text-lg md:text-xl font-bold font-display text-mitti-900 dark:text-kora-100">{t('chat.title')}</h2>
            <p className="text-xs text-mitti-500 dark:text-mitti-400">{t('chat.subtitle')}</p>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-4">
        <AnimatePresence>
          {messages.map((message) => (
            <motion.div
              key={message.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex items-start space-x-3 ${message.role === 'user' ? 'flex-row-reverse space-x-reverse' : ''}`}
            >
              <div className={`flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center shadow-sm ${
                message.role === 'user'
                  ? 'bg-gradient-to-br from-neel-500 to-neel-600'
                  : 'bg-gradient-to-br from-mitti-500 to-mitti-600'
              }`}>
                {message.role === 'user' ? <User className="w-4 h-4 text-white" /> : <Bot className="w-4 h-4 text-white" />}
              </div>
              <div className={`flex-1 max-w-3xl ${message.role === 'user' ? 'flex justify-end' : ''}`}>
                <div className={`rounded-2xl px-5 py-3.5 ${
                  message.role === 'user'
                    ? 'bg-neel-500 text-white shadow-neel'
                    : 'village-card'
                }`}>
                  {message.loading ? (
                    <div className="flex items-center space-x-2">
                      <div className="flex space-x-1">
                        <span className="w-2 h-2 bg-mitti-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                        <span className="w-2 h-2 bg-mitti-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                        <span className="w-2 h-2 bg-mitti-600 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                      </div>
                      <span className="text-mitti-500 dark:text-mitti-400 text-sm">{t('chat.thinking')}</span>
                    </div>
                  ) : (
                    <div className="whitespace-pre-wrap leading-relaxed text-sm"
                      dangerouslySetInnerHTML={{ __html: message.content.replace(/\n/g, '<br/>') }}
                    />
                  )}
                </div>
                <p className={`text-[10px] text-mitti-400 mt-1 px-2 ${message.role === 'user' ? 'text-right' : ''}`}>
                  {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </p>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
        <div ref={messagesEndRef} />
      </div>

      {/* Empty State / Suggested Questions */}
      {messages.filter(m => m.role === 'user').length === 0 && (
        <div className="px-4 md:px-6 py-3">
          <p className="text-xs text-mitti-500 dark:text-mitti-400 mb-2 font-medium flex items-center">
            <Sparkles className="w-3.5 h-3.5 mr-1.5 text-mitti-500" />{t('chat.suggestedQuestions')}
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {suggestedQuestions.map((q, i) => (
              <motion.button key={i} onClick={() => { setInput(q); inputRef.current?.focus(); }}
                className="text-left p-3 village-card-subtle hover:border-mitti-500/40 transition-all text-sm text-mitti-600 dark:text-kora-200 hover:text-mitti-700"
                whileHover={{ x: 4 }}>
                {q}
              </motion.button>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <div className="village-card border-t border-mitti-200/20 dark:border-night-border/40 p-3 md:p-4">
        <div className="max-w-4xl mx-auto flex items-end space-x-3">
          <div className="flex-1">
            <input ref={inputRef} type="text" value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), handleSend())}
              placeholder={language === 'hi' ? t('chat.placeholderHi') : t('chat.placeholder')}
              disabled={isTyping}
              className="village-input disabled:opacity-50 disabled:cursor-not-allowed"
            />
          </div>
          <VoiceInputButton
            onTranscription={(text) => setInput(text)}
            size="sm"
          />
          <motion.button onClick={handleSend} disabled={!input.trim() || isTyping}
            className={`p-3.5 rounded-xl font-medium transition-all ${
              input.trim() && !isTyping
                ? 'btn-mitti py-3.5 px-3.5'
                : 'bg-mitti-200 dark:bg-night-bg text-mitti-400 cursor-not-allowed'
            }`}
            whileHover={input.trim() && !isTyping ? { scale: 1.05 } : {}}
            whileTap={input.trim() && !isTyping ? { scale: 0.95 } : {}}
          >
            {isTyping ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
          </motion.button>
        </div>
      </div>
    </PageTransition>
  );
};

export default Chat;
