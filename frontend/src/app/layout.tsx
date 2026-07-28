import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "SmartClass AI | Modern Academic & Virtual Learning Platform",
  description:
    "An AI-powered academic ecosystem integrating virtual classrooms, learning management, smart assessments, AI tutoring, facial attendance, engagement analytics, and personalized learning twins.",
  keywords: [
    "SmartClass AI",
    "EdTech",
    "AI Tutor",
    "Virtual Classroom",
    "Learning Twin",
    "AI Proctoring",
    "Facial Attendance",
    "Learning Graph",
    "Academic Analytics",
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} light`}>
      <head>
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200"
        />
      </head>
      <body className={`${inter.className} min-h-screen flex flex-col antialiased selection:bg-[#c3f185] selection:text-[#112000]`}>
        {children}
      </body>
    </html>
  );
}
