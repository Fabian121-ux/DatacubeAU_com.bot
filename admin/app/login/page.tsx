import { Suspense } from 'react';
import LoginClientPage from './login-client';

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[var(--app-bg)]" />}>
      <LoginClientPage />
    </Suspense>
  );
}

