import { useState } from 'react';
import { Navbar } from './components/Navbar';
import { BabaStage } from './components/BabaStage';
import {
  ConversationAnalysisPanel,
  type Message,
  type ArchitectureStateInfo
} from './components/ConversationAnalysisPanel';
import { FooterBar } from './components/FooterBar';
import { MessageSquare, X } from 'lucide-react';
import {
  mapCitationsForUi,
  mapRagResponseToArchitectureState,
  queryRag,
  RagApiError,
} from './services/ragApi';

const INITIAL_BABA_GREETING =
  'Namaste! I am Baba Ji, your guide to Indian IP and traditional knowledge law. Ask by voice or text — I will search the indexed corpus and answer with citations.';

export function App() {
  const [isMobilePanelOpen, setIsMobilePanelOpen] = useState<boolean>(false);
  const [isSpeaking, setIsSpeaking] = useState<boolean>(false);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);

  const [currentSpokenText, setCurrentSpokenText] = useState<string>(INITIAL_BABA_GREETING);

  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      sender: 'baba',
      text: INITIAL_BABA_GREETING,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);

  const [architectureState, setArchitectureState] = useState<ArchitectureStateInfo>({
    step: 'understanding',
    detectedEntities: ['Awaiting your question'],
    formulationCategory: '—',
    legalRegime: 'Indexed IP & traditional-knowledge corpus',
    confidenceScore: '—',
    confidenceTier: '—',
  });

  const handleUserSubmit = async (userText: string) => {
    const trimmed = userText.trim();
    if (!trimmed) return;

    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    const userMsg: Message = {
      id: Date.now().toString(),
      sender: 'user',
      text: trimmed,
      time: timeStr,
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsProcessing(true);
    setArchitectureState((prev) => ({
      ...prev,
      step: 'retrieval',
      confidenceScore: '…',
      confidenceTier: '…',
    }));

    try {
      const response = await queryRag(trimmed);
      const citations = mapCitationsForUi(response.citations ?? [], response.evidence ?? []);

      const babaMsg: Message = {
        id: (Date.now() + 1).toString(),
        sender: 'baba',
        text: response.answer,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        citations: citations.length > 0 ? citations : undefined,
        grounded: response.grounded,
      };

      setMessages((prev) => [...prev, babaMsg]);
      setCurrentSpokenText(response.answer);
      setArchitectureState(mapRagResponseToArchitectureState(response));
    } catch (err) {
      const message =
        err instanceof RagApiError
          ? err.message
          : 'Something went wrong while searching the knowledge base.';

      const babaMsg: Message = {
        id: (Date.now() + 1).toString(),
        sender: 'baba',
        text: message,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        grounded: false,
      };

      setMessages((prev) => [...prev, babaMsg]);
      setArchitectureState((prev) => ({
        ...prev,
        step: 'validation',
        confidenceScore: '—',
        confidenceTier: 'Error',
      }));
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="h-screen w-screen flex flex-col bg-[#0B0E14] text-slate-100 overflow-hidden font-sans select-none">
      <Navbar currentJurisdiction="India (IPA 1970 & Section 3(p))" />

      <main className="flex-1 flex flex-col lg:flex-row overflow-hidden relative">
        <BabaStage
          onUserSubmit={handleUserSubmit}
          onSpeakingChange={setIsSpeaking}
          isSpeaking={isSpeaking}
          activeClarification={null}
          currentSpokenText={currentSpokenText}
          isProcessing={isProcessing}
        />

        <div className="hidden lg:block h-full">
          <ConversationAnalysisPanel
            messages={messages}
            onSendQuery={handleUserSubmit}
            isSpeaking={isSpeaking}
            isProcessing={isProcessing}
            activeClarification={null}
            architectureState={architectureState}
          />
        </div>

        <div className="lg:hidden absolute bottom-14 right-4 z-30">
          <button
            onClick={() => setIsMobilePanelOpen(!isMobilePanelOpen)}
            className="flex items-center space-x-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-4 py-2.5 rounded-full font-semibold shadow-xl border border-white/20 active:scale-95 transition-all text-xs"
          >
            <MessageSquare className="w-4 h-4" />
            <span>{isMobilePanelOpen ? 'Close Panel' : 'Conversation & Analysis'}</span>
          </button>
        </div>

        {isMobilePanelOpen && (
          <div className="lg:hidden fixed inset-0 z-40 bg-black/70 backdrop-blur-sm flex flex-col justify-end">
            <div className="bg-[#0E131F] border-t border-white/15 rounded-t-2xl h-[85vh] flex flex-col shadow-2xl relative overflow-hidden">
              <div className="p-3 bg-[#0B0E14] border-b border-white/10 flex items-center justify-between">
                <span className="font-sans font-semibold text-sm text-white">
                  Conversation & Legal Analysis
                </span>
                <button
                  onClick={() => setIsMobilePanelOpen(false)}
                  className="p-1 rounded-lg text-slate-400 hover:text-white"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              <div className="flex-1 overflow-hidden">
                <ConversationAnalysisPanel
                  messages={messages}
                  onSendQuery={handleUserSubmit}
                  isSpeaking={isSpeaking}
                  isProcessing={isProcessing}
                  activeClarification={null}
                  architectureState={architectureState}
                />
              </div>
            </div>
          </div>
        )}
      </main>

      <FooterBar />
    </div>
  );
}

export default App;
