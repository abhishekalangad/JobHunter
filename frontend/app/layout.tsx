import type { Metadata } from 'next';
import './globals.css';
import { Toaster } from 'react-hot-toast';

export const metadata: Metadata = {
  title: 'AI Job Hunter | RAG-Powered Job Application System',
  description: 'Intelligently match your resume to job descriptions using AI, generate personalized emails, and track your applications.',
  keywords: ['job application', 'AI', 'resume matching', 'RAG', 'job hunting'],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" />
      </head>
      <body style={{ fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif" }}>
        {children}
        <Toaster
          position="top-right"
          toastOptions={{
            style: {
              background: '#16161f',
              color: '#f1f5f9',
              border: '1px solid rgba(255,255,255,0.07)',
              borderRadius: '10px',
            },
            success: { iconTheme: { primary: '#10b981', secondary: '#16161f' } },
            error:   { iconTheme: { primary: '#f43f5e', secondary: '#16161f' } },
          }}
        />
      </body>
    </html>
  );
}
