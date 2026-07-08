import { Link } from 'react-router-dom';
import type { FC, ReactNode } from 'react';

interface AuthLayoutProps {
  title: string;
  subtitle: string;
  linkText: string;
  linkTo: string;
  children: ReactNode;
}

export const AuthLayout: FC<AuthLayoutProps> = ({
  title,
  subtitle,
  linkText,
  linkTo,
  children,
}) => {
  return (
    <div className="min-h-screen auth-grid-bg flex">
      <div className="hidden lg:flex lg:w-1/2 flex-col justify-between p-12 relative overflow-hidden">
        <div className="absolute inset-0 opacity-30">
          <div className="absolute top-20 left-10 w-72 h-72 bg-indigo-500/20 rounded-full blur-3xl" />
          <div className="absolute bottom-20 right-10 w-96 h-96 bg-violet-500/15 rounded-full blur-3xl" />
        </div>

        <div className="relative z-10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/30">
              <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <span className="text-white font-bold text-xl tracking-tight">Masidonia</span>
          </div>
        </div>

        <div className="relative z-10 space-y-6">
          <h1 className="text-4xl xl:text-5xl font-extrabold text-white leading-tight">
            Query resumes<br />
            <span className="bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent">
              with AI precision
            </span>
          </h1>
          <p className="text-slate-400 text-lg max-w-md leading-relaxed">
            Upload PDF or DOCX resumes and ask natural language questions. Get instant, source-backed answers.
          </p>
          <div className="flex gap-6 pt-2">
            {[
              { label: 'Smart parsing', icon: '⚡' },
              { label: 'Source citations', icon: '📎' },
              { label: 'Secure auth', icon: '🔒' },
            ].map((item) => (
              <div key={item.label} className="flex items-center gap-2 text-slate-400 text-sm">
                <span>{item.icon}</span>
                <span>{item.label}</span>
              </div>
            ))}
          </div>
        </div>

        <p className="relative z-10 text-slate-600 text-sm">
          © {new Date().getFullYear()} Masidonia. All rights reserved.
        </p>
      </div>

      <div className="flex-1 flex items-center justify-center p-6 sm:p-10">
        <div className="w-full max-w-md">
          <div className="lg:hidden flex items-center gap-3 mb-8 justify-center">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center">
              <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <span className="text-white font-bold text-lg">Masidonia</span>
          </div>

          <div className="glass-card rounded-2xl p-8 shadow-2xl shadow-black/20">
            <div className="mb-8">
              <h2 className="text-2xl font-bold text-white">{title}</h2>
              <p className="mt-2 text-slate-400 text-sm">
                {subtitle}{' '}
                <Link to={linkTo} className="text-indigo-400 hover:text-indigo-300 font-medium transition-colors">
                  {linkText}
                </Link>
              </p>
            </div>
            {children}
          </div>
        </div>
      </div>
    </div>
  );
};
