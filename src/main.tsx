import {StrictMode} from 'react';
import {createRoot} from 'react-dom/client';
import App from './App.tsx';
import { MotionConfig } from 'motion/react';
import { FeedbackProvider } from './components/ui/feedback';
import './index.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {/* "user": motion animations follow the system's reduced-motion setting
        (#31). The default ignored it, so the sign-in card still slid in. */}
    <MotionConfig reducedMotion="user">
      <FeedbackProvider>
        <App />
      </FeedbackProvider>
    </MotionConfig>
  </StrictMode>,
);
