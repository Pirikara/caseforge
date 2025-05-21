import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import dynamic from "next/dynamic";
import { Toaster } from "./components/ui/sonner";
import { UIModeProviderClient } from "./components/UIModeProviderClient";

// 動的インポート
const ThemeProvider = dynamic(() => import("./components/ThemeProvider").then(mod => mod.ThemeProvider), { ssr: true });
const Header = dynamic(() => import("./components/organisms/Header").then(mod => mod.Header), { ssr: true });
const Sidebar = dynamic(() => import("./components/organisms/Sidebar").then(mod => mod.Sidebar), { ssr: true });
const Footer = dynamic(() => import("./components/organisms/Footer").then(mod => mod.Footer), { ssr: true });

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Caseforge - OpenAPIテスト自動化ツール",
  description: "OpenAPIスキーマに基づくAIテストケースの生成・実行・可視化を行うOSSツール",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ja" suppressHydrationWarning>
      <body className={inter.className}>
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <UIModeProviderClient>
            <div className="flex min-h-screen flex-col">
              <Header className="md:hidden" />
              <div className="flex flex-1">
                <Sidebar className="hidden md:block" />
                <main className="flex-1 p-4 md:p-6 md:ml-64">{children}</main>
              </div>
              <Footer />
            </div>
          </UIModeProviderClient>
          <Toaster />
        </ThemeProvider>
      </body>
    </html>
  );
}
