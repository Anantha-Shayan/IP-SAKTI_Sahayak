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
  processUserQuestion,
  resolveFullPipeline
} from './services/architecturePipeline';

export function App() {
  const [isMobilePanelOpen, setIsMobilePanelOpen] = useState<boolean>(false);
  const [isSpeaking, setIsSpeaking] = useState<boolean>(false);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);

  // Spoken text to feed into BabaStage TTS
  const [currentSpokenText, setCurrentSpokenText] = useState<string>(
    "That is an important question. Under Section 3(p) of the Indian Patents Act, traditional knowledge per se is non-patentable. To evaluate your claim against classical Samhitas, can you clarify: what exact modification have you made — an unexpected synergistic ratio, a novel extraction process, or a novel drug delivery carrier?"
  );

  // Initial conversation starts with Baba Ji asking clarification per system architecture
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      sender: 'user',
      text: 'Can I patent a modified version of an Ayurvedic formulation?',
      time: '10:24 AM',
    },
    {
      id: '2',
      sender: 'baba',
      text: "That is an important question. Under Section 3(p) of the Indian Patents Act, traditional knowledge per se is non-patentable. To evaluate your claim against classical Samhitas, can you clarify: what exact modification have you made — an unexpected synergistic ratio, a novel extraction process, or a novel drug delivery carrier?",
      time: '10:24 AM',
      isClarification: true,
    },
  ]);

  // Active clarification requested by Baba Ji according to architecture
  const [activeClarification, setActiveClarification] = useState<{
    question: string;
    chips: string[];
  } | null>({
    question: 'What exact modification have you made to the classical formulation?',
    chips: [
      'Synergistic Herbal Ratio (Section 3(e))',
      'Novel Drug Delivery / Nano-carrier (Section 3(d))',
      'Standardized Bioactive Extraction Method',
    ],
  });

  // Track the 6. End-to-End System Architecture state
  const [architectureState, setArchitectureState] = useState<ArchitectureStateInfo>({
    step: 'clarification',
    detectedEntities: ['Curcuma longa (Haridra)', 'Azadirachta indica (Nimba)'],
    formulationCategory: 'Classical Ayurvedic Formulation (Base)',
    legalRegime: 'India (IPA 1970 · Section 3(p) Evaluation)',
    confidenceScore: '92%',
    confidenceTier: 'High',
  });

  // Central User Submission Handler: handles speech-to-text, clarification chip taps, or typed prompts
  const handleUserSubmit = (userText: string) => {
    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    const userMsg: Message = {
      id: Date.now().toString(),
      sender: 'user',
      text: userText,
      time: timeStr,
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsProcessing(true);

    setTimeout(() => {
      if (activeClarification) {
        // User is answering Baba Ji's clarifying question
        const result = resolveFullPipeline(userText, architectureState.detectedEntities, userText);

        const babaMsg: Message = {
          id: (Date.now() + 1).toString(),
          sender: 'baba',
          text: result.immediateAnswer,
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          citations: result.retrievedCitations,
        };

        setMessages((prev) => [...prev, babaMsg]);
        setActiveClarification(null);
        setCurrentSpokenText(result.immediateAnswer);
        setArchitectureState({
          step: 'complete',
          detectedEntities: result.extractedEntities,
          formulationCategory: result.formulationCategory,
          legalRegime: result.legalRegime,
          confidenceScore: result.confidenceScore,
          confidenceTier: result.confidenceTier,
        });
        setIsProcessing(false);
      } else {
        // User asks a new formulation question
        const result = processUserQuestion(userText);

        if (result.requiresClarification && result.clarifyingQuestion && result.clarificationChips) {
          // Baba Ji asks a clarifying question according to the architecture
          const babaMsg: Message = {
            id: (Date.now() + 1).toString(),
            sender: 'baba',
            text: result.clarifyingQuestion,
            time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            isClarification: true,
          };

          setMessages((prev) => [...prev, babaMsg]);
          setActiveClarification({
            question: 'What exact modification have you made to the formulation?',
            chips: result.clarificationChips,
          });
          setCurrentSpokenText(result.clarifyingQuestion);
          setArchitectureState({
            step: 'clarification',
            detectedEntities: result.extractedEntities,
            formulationCategory: result.formulationCategory,
            legalRegime: result.legalRegime,
            confidenceScore: result.confidenceScore,
            confidenceTier: result.confidenceTier,
          });
          setIsProcessing(false);
        } else {
          // Complete answer with citations
          const babaMsg: Message = {
            id: (Date.now() + 1).toString(),
            sender: 'baba',
            text: result.immediateAnswer || '',
            time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            citations: result.retrievedCitations,
          };

          setMessages((prev) => [...prev, babaMsg]);
          setActiveClarification(null);
          if (result.immediateAnswer) {
            setCurrentSpokenText(result.immediateAnswer);
          }
          setArchitectureState({
            step: 'complete',
            detectedEntities: result.extractedEntities,
            formulationCategory: result.formulationCategory,
            legalRegime: result.legalRegime,
            confidenceScore: result.confidenceScore,
            confidenceTier: result.confidenceTier,
          });
          setIsProcessing(false);
        }
      }
    }, 700);
  };

  return (
    <div className="h-screen w-screen flex flex-col bg-[#0B0E14] text-slate-100 overflow-hidden font-sans select-none">
      {/* Top System Navigation Bar (From Mockup) */}
      <Navbar currentJurisdiction="India (IPA 1970 & Section 3(p))" />

      {/* Main Workspace Split View */}
      <main className="flex-1 flex flex-col lg:flex-row overflow-hidden relative">
        {/* Left Side: Ayurvedic Scholar Stage & Voice Control Bar */}
        <BabaStage
          onUserSubmit={handleUserSubmit}
          onSpeakingChange={setIsSpeaking}
          isSpeaking={isSpeaking}
          activeClarification={activeClarification}
          onAnswerClarification={(chip) => handleUserSubmit(chip)}
          currentSpokenText={currentSpokenText}
          isProcessing={isProcessing}
        />

        {/* Right Side: Conversation & Legal Analysis Panel (Desktop) */}
        <div className="hidden lg:block h-full">
          <ConversationAnalysisPanel
            messages={messages}
            onSendQuery={handleUserSubmit}
            isSpeaking={isSpeaking}
            isProcessing={isProcessing}
            activeClarification={activeClarification}
            onSelectClarificationChip={(chip) => handleUserSubmit(chip)}
            architectureState={architectureState}
          />
        </div>

        {/* Mobile Toggle Floating Button for Analysis Panel */}
        <div className="lg:hidden absolute bottom-14 right-4 z-30">
          <button
            onClick={() => setIsMobilePanelOpen(!isMobilePanelOpen)}
            className="flex items-center space-x-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-4 py-2.5 rounded-full font-semibold shadow-xl border border-white/20 active:scale-95 transition-all text-xs"
          >
            <MessageSquare className="w-4 h-4" />
            <span>{isMobilePanelOpen ? 'Close Panel' : 'Conversation & Analysis'}</span>
          </button>
        </div>

        {/* Mobile Bottom-Sheet Overlay for Analysis Panel */}
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
                  activeClarification={activeClarification}
                  onSelectClarificationChip={(chip) => handleUserSubmit(chip)}
                  architectureState={architectureState}
                />
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Bottom Footer Bar (From Mockup) */}
      <FooterBar />
    </div>
  );
}

export default App;
