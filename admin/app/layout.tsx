import type { Metadata } from 'next';
import { Space_Grotesk, IBM_Plex_Mono } from 'next/font/google';
import './globals.css';

const titleFont = Space_Grotesk({
  subsets: ['latin'],
  variable: '--font-title'
});

const monoFont = IBM_Plex_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
  weight: ['400', '500']
});

export const metadata: Metadata = {
  title: 'Datacube AU Bot Admin',
  description: 'Secure control panel for Datacube AU WhatsApp Bot'
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${titleFont.variable} ${monoFont.variable}`}>
        {children}
      </body>
    </html>
  );
}
