"use client";

import React, { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  consumeInitialAccessTokenCookie,
  setMemoryAccessToken,
  refreshAuthSession,
  fetchCurrentUser,
} from "../../../lib/auth";

function AuthCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const authError = searchParams.get("error");
    if (authError) {
      setError(decodeURIComponent(authError));
      return;
    }

    const initSession = async () => {
      const initToken = consumeInitialAccessTokenCookie();
      if (initToken) {
        setMemoryAccessToken(initToken);
      }

      let userProfile = await fetchCurrentUser();
      if (!userProfile) {
        const session = await refreshAuthSession();
        if (session) {
          userProfile = session.user;
        }
      }

      if (userProfile) {
        router.replace("/classroom");
      } else {
        setError("Failed to establish authentication session.");
      }
    };

    initSession();
  }, [searchParams, router]);

  if (error) {
    return (
      <div className="min-h-screen bg-[#fcf9f8] dark:bg-[#141816] text-[#1c1b1b] dark:text-[#e1e4e1] flex items-center justify-center p-6">
        <div className="max-w-md w-full p-8 rounded-3xl bg-white dark:bg-[#1b211e] border border-[#ebe7e7] dark:border-[#2f3732] shadow-2xl text-center space-y-6">
          <div className="w-16 h-16 rounded-full bg-red-500/10 text-red-500 flex items-center justify-center mx-auto text-3xl font-bold">
            !
          </div>
          <h2 className="text-2xl font-bold">Authentication Error</h2>
          <p className="text-sm text-[#404945] dark:text-[#c0c8c4]">{error}</p>
          <button
            onClick={() => router.push("/login")}
            className="w-full py-4 bg-[#154539] dark:bg-[#a0d1c0] text-white dark:text-[#00372d] rounded-full font-semibold hover:opacity-90 transition-all cursor-pointer"
          >
            Back to Sign In
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#fcf9f8] dark:bg-[#141816] text-[#1c1b1b] dark:text-[#e1e4e1] flex items-center justify-center p-6">
      <div className="max-w-md w-full p-8 rounded-3xl bg-white dark:bg-[#1b211e] border border-[#ebe7e7] dark:border-[#2f3732] shadow-2xl text-center space-y-6">
        <div className="w-12 h-12 border-4 border-[#154539] dark:border-[#a0d1c0] border-t-transparent rounded-full animate-spin mx-auto"></div>
        <h2 className="text-2xl font-bold">Authenticating...</h2>
        <p className="text-sm text-[#404945] dark:text-[#c0c8c4]">
          Verifying your identity securely. Please wait...
        </p>
      </div>
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-[#fcf9f8] dark:bg-[#141816] text-[#1c1b1b] dark:text-[#e1e4e1] flex items-center justify-center p-6">
        <div className="max-w-md w-full p-8 rounded-3xl bg-white dark:bg-[#1b211e] border border-[#ebe7e7] dark:border-[#2f3732] text-center space-y-4 shadow-xl animate-pulse">
          <div className="w-12 h-12 border-4 border-[#154539] dark:border-[#a0d1c0] border-t-transparent rounded-full animate-spin mx-auto"></div>
          <p className="text-sm font-semibold">Loading authentication callback...</p>
        </div>
      </div>
    }>
      <AuthCallbackContent />
    </Suspense>
  );
}
