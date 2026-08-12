'use client';

import { useState } from 'react';
import Sidebar from '@/components/Sidebar';
import Dashboard from '@/components/Dashboard';
import ResumeManager from '@/components/ResumeManager';
import JDMatcher from '@/components/JDMatcher';
import ApplicationTracker from '@/components/ApplicationTracker';

export type ActiveView = 'dashboard' | 'resumes' | 'jd-match' | 'applications';

export default function Home() {
  const [activeView, setActiveView] = useState<ActiveView>('dashboard');

  const renderView = () => {
    switch (activeView) {
      case 'dashboard':      return <Dashboard onNavigate={setActiveView} />;
      case 'resumes':        return <ResumeManager />;
      case 'jd-match':       return <JDMatcher />;
      case 'applications':   return <ApplicationTracker />;
      default:               return <Dashboard onNavigate={setActiveView} />;
    }
  };

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden', background: 'var(--bg-primary)' }}>
      <Sidebar activeView={activeView} onNavigate={setActiveView} />
      <main style={{ flex: 1, overflowY: 'auto', padding: '32px' }}>
        {renderView()}
      </main>
    </div>
  );
}
