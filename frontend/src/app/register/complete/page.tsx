"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Country, State, City } from "country-state-city";
import { getMemoryAccessToken, API_BASE_URL, fetchCurrentUser } from "../../../lib/auth";

export default function CompleteRegistrationPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [checkingAuth, setCheckingAuth] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // User details
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [phone, setPhone] = useState("");

  const [orgName, setOrgName] = useState("");
  const [orgSlug, setOrgSlug] = useState("");
  const [isSlugManuallyEdited, setIsSlugManuallyEdited] = useState(false);

  const slugify = (text: string) => {
    return text
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/(^-|-$)+/g, "");
  };
  const [orgType, setOrgType] = useState("University");
  const [selectedCountry, setSelectedCountry] = useState("");
  const [selectedState, setSelectedState] = useState("");
  const [selectedCity, setSelectedCity] = useState("");
  const [selectedTimezone, setSelectedTimezone] = useState("");
  const [orgDescription, setOrgDescription] = useState("");

  // Workspace details
  const [workspaceName, setWorkspaceName] = useState("Main Workspace");

  // Availability checks
  const [nameAvailable, setNameAvailable] = useState<boolean | null>(null);
  const [slugAvailable, setSlugAvailable] = useState<boolean | null>(null);

  // country-state-city data arrays
  const [countriesList, setCountriesList] = useState<any[]>([]);
  const [statesList, setStatesList] = useState<any[]>([]);
  const [citiesList, setCitiesList] = useState<any[]>([]);
  const [timezonesList, setTimezonesList] = useState<any[]>([]);

  useEffect(() => {
    // 1. Authenticate check
    const checkAuth = async () => {
      const token = getMemoryAccessToken();
      const user = await fetchCurrentUser();
      if (!token || !user) {
        router.replace("/login");
        return;
      }
      
      // Seed user names from profile if exists
      if (user.first_name) setFirstName(user.first_name);
      if (user.last_name) setLastName(user.last_name);
      
      setCheckingAuth(false);
    };

    checkAuth();

    // 2. Load countries
    setCountriesList(Country.getAllCountries());
  }, [router]);

  // Handle Country selection
  const handleCountryChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const countryCode = e.target.value;
    setSelectedCountry(countryCode);
    setSelectedState("");
    setSelectedCity("");
    setSelectedTimezone("");
    setCitiesList([]);

    if (countryCode) {
      setStatesList(State.getStatesOfCountry(countryCode));
      const countryData = Country.getCountryByCode(countryCode);
      if (countryData?.timezones) {
        setTimezonesList(countryData.timezones);
        if (countryData.timezones.length > 0) {
          setSelectedTimezone(countryData.timezones[0].zoneName);
        }
      } else {
        setTimezonesList([]);
      }
    } else {
      setStatesList([]);
      setTimezonesList([]);
    }
  };

  // Handle State selection
  const handleStateChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const stateCode = e.target.value;
    setSelectedState(stateCode);
    setSelectedCity("");

    if (selectedCountry && stateCode) {
      setCitiesList(City.getCitiesOfState(selectedCountry, stateCode));
    } else {
      setCitiesList([]);
    }
  };

  // Debounced Name Check
  useEffect(() => {
    if (!orgName.trim()) {
      setNameAvailable(null);
      return;
    }
    const timer = setTimeout(async () => {
      try {
        const res = await fetch(
          `${API_BASE_URL}/organizations/check-name?name=${encodeURIComponent(orgName)}`
        );
        if (res.ok) {
          const data = await res.json();
          setNameAvailable(data.available);
        }
      } catch (err) {}
    }, 450);
    return () => clearTimeout(timer);
  }, [orgName]);

  // Debounced Slug Check
  useEffect(() => {
    if (!orgSlug.trim()) {
      setSlugAvailable(null);
      return;
    }
    const timer = setTimeout(async () => {
      try {
        const res = await fetch(
          `${API_BASE_URL}/organizations/check-slug?slug=${encodeURIComponent(orgSlug)}`
        );
        if (res.ok) {
          const data = await res.json();
          setSlugAvailable(data.available);
        }
      } catch (err) {}
    }, 450);
    return () => clearTimeout(timer);
  }, [orgSlug]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (nameAvailable === false) {
      setError("Organization name is already taken.");
      return;
    }
    if (slugAvailable === false) {
      setError("URL Slug is already taken.");
      return;
    }

    setLoading(true);

    try {
      const token = getMemoryAccessToken();
      const countryName = Country.getCountryByCode(selectedCountry)?.name || selectedCountry;
      const stateName = State.getStateByCodeAndCountry(selectedState, selectedCountry)?.name || selectedState;

      const payload = {
        org_name: orgName,
        org_slug: orgSlug,
        org_type: orgType,
        org_country: countryName,
        org_state: stateName,
        org_city: selectedCity,
        org_timezone: selectedTimezone,
        org_description: orgDescription,
        owner_first_name: firstName,
        owner_last_name: lastName,
        owner_phone: phone || null,
        workspace_name: workspaceName,
      };

      const res = await fetch(`${API_BASE_URL}/organizations/onboarding`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail?.message || "Failed to complete onboarding.");
      }

      router.replace("/classroom");
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred during onboarding.");
    } finally {
      setLoading(false);
    }
  };

  if (checkingAuth) {
    return (
      <div className="min-h-screen bg-[var(--background)] text-[var(--on-surface)] flex items-center justify-center p-6">
        <div className="max-w-md w-full p-8 rounded-3xl bg-white dark:bg-[#1b211e] border border-[var(--outline-variant)]/30 text-center space-y-4 shadow-xl animate-pulse">
          <div className="w-12 h-12 border-4 border-[var(--primary)] border-t-transparent rounded-full animate-spin mx-auto"></div>
          <p className="text-sm font-semibold">Verifying session details...</p>
        </div>
      </div>
    );
  }

  return (
    <main className="min-h-screen flex flex-col md:flex-row p-4 md:p-8 lg:p-12 gap-8 lg:gap-gutter bg-[var(--background)] text-[var(--on-surface)] font-body-md overflow-x-hidden">
      {/* Left Column: Visual Motif */}
      <section className="relative w-full md:w-[45%] bg-[var(--primary)] min-h-[400px] rounded-lg overflow-hidden flex flex-col justify-between p-8 lg:p-16">
        {/* Brand Mark */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-[var(--primary-fixed)] rounded-full flex items-center justify-center">
            <span className="material-symbols-outlined text-[var(--primary)] text-[24px]">school</span>
          </div>
          <span className="text-headline-md font-headline-md font-bold text-[var(--on-primary)]">SmartClass AI</span>
        </div>

        <div className="relative z-10 space-y-6">
          <div className="max-w-md">
            <h2 className="text-3xl font-bold text-[var(--primary-fixed)] mb-4 leading-tight">Complete your institutional setup.</h2>
            <p className="text-body-md text-[var(--on-primary)]/80 leading-relaxed">
              Define your organization’s identity, location parameters, and create the first workspace to welcome scholars and instructors.
            </p>
          </div>

          <div className="space-y-3 pt-4 border-t border-[#ebe7e7]/20">
            <div className="flex items-center gap-3">
              <span className="material-symbols-outlined text-[var(--tertiary-fixed)]">check_circle</span>
              <span className="text-sm font-medium text-[var(--on-primary)]/90">Single tenant workspace isolated transactionally</span>
            </div>
            <div className="flex items-center gap-3">
              <span className="material-symbols-outlined text-[var(--tertiary-fixed)]">check_circle</span>
              <span className="text-sm font-medium text-[var(--on-primary)]/90">Auto-generated Owner and Admin permissions</span>
            </div>
          </div>
        </div>

        {/* Background organic path */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none opacity-20" preserveAspectRatio="none" viewBox="0 0 400 400">
          <path className="organic-path" d="M0,200 C100,50 300,350 400,200" fill="none" stroke="white" strokeWidth="2"></path>
        </svg>
      </section>

      {/* Right Column: Setup Form */}
      <section className="w-full md:w-[55%] flex flex-col justify-center px-4 md:px-8 py-4">
        <div className="w-full max-w-xl mx-auto bg-white dark:bg-[#1b211e] border border-[var(--outline-variant)]/30 p-8 rounded-[32px] shadow-lg">
          <header className="mb-8">
            <div className="flex items-center gap-2 mb-3">
              <span className="w-8 h-1 bg-[var(--secondary-container)] rounded-full"></span>
              <span className="text-label-sm uppercase tracking-widest text-[var(--secondary)]">Step 2 of 2</span>
            </div>
            <h1 className="text-3xl font-bold text-[var(--primary)] mb-1">Set Up Organization</h1>
            <p className="text-sm text-[var(--on-surface-variant)]">Let's build your brand-new digital academy space.</p>
          </header>

          {error && (
            <div className="mb-6 p-4 rounded-2xl bg-red-500/10 border border-red-500/30 text-red-500 text-sm font-medium flex items-center gap-2">
              <span className="material-symbols-outlined text-[20px]">error</span>
              <span>{error}</span>
            </div>
          )}

          <form className="space-y-6" onSubmit={handleSubmit}>
            {/* Owner Section */}
            <div className="space-y-4">
              <h3 className="text-sm font-bold uppercase tracking-wider text-[var(--primary)] border-b pb-1.5">1. Owner Profile Details</h3>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-[var(--on-surface-variant)]" htmlFor="firstName">First Name</label>
                  <input
                    className="w-full px-5 py-3 bg-[var(--surface-container)] border-2 border-transparent focus:border-[var(--primary)] rounded-full transition-all outline-none text-sm text-[var(--on-surface)]"
                    id="firstName"
                    type="text"
                    value={firstName}
                    onChange={(e) => setFirstName(e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-[var(--on-surface-variant)]" htmlFor="lastName">Last Name</label>
                  <input
                    className="w-full px-5 py-3 bg-[var(--surface-container)] border-2 border-transparent focus:border-[var(--primary)] rounded-full transition-all outline-none text-sm text-[var(--on-surface)]"
                    id="lastName"
                    type="text"
                    value={lastName}
                    onChange={(e) => setLastName(e.target.value)}
                    required
                  />
                </div>
              </div>
              <div className="space-y-1">
                <label className="text-xs font-semibold text-[var(--on-surface-variant)]" htmlFor="phone">Contact Number (Optional)</label>
                <input
                  className="w-full px-5 py-3 bg-[var(--surface-container)] border-2 border-transparent focus:border-[var(--primary)] rounded-full transition-all outline-none text-sm text-[var(--on-surface)]"
                  id="phone"
                  type="text"
                  placeholder="+1 (555) 019-2834"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                />
              </div>
            </div>

            {/* Organization Profile Section */}
            <div className="space-y-4 pt-2">
              <h3 className="text-sm font-bold uppercase tracking-wider text-[var(--primary)] border-b pb-1.5">2. Organization Details</h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Org Name */}
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-[var(--on-surface-variant)]" htmlFor="orgName">Organization Name</label>
                  <div className="relative">
                    <input
                      className={`w-full px-5 py-3 bg-[var(--surface-container)] border-2 border-transparent focus:ring-0 rounded-full transition-all outline-none text-sm text-[var(--on-surface)] ${
                        nameAvailable === true
                          ? "focus:border-emerald-500"
                          : nameAvailable === false
                          ? "focus:border-red-500"
                          : "focus:border-[var(--primary)]"
                      }`}
                      id="orgName"
                      type="text"
                      placeholder="Stark Academy of Science"
                      value={orgName}
                      onChange={(e) => {
                        const val = e.target.value;
                        setOrgName(val);
                        if (!isSlugManuallyEdited) {
                          setOrgSlug(slugify(val));
                        }
                      }}
                      required
                    />
                    {nameAvailable !== null && (
                      <span className={`material-symbols-outlined absolute right-4 top-1/2 -translate-y-1/2 text-sm ${
                        nameAvailable ? "text-emerald-500" : "text-red-500"
                      }`}>
                        {nameAvailable ? "check_circle" : "cancel"}
                      </span>
                    )}
                  </div>
                </div>

                {/* Org Slug */}
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-[var(--on-surface-variant)]" htmlFor="orgSlug">URL Slug</label>
                  <div className="relative">
                    <input
                      className={`w-full px-5 py-3 bg-[var(--surface-container)] border-2 border-transparent focus:ring-0 rounded-full transition-all outline-none text-sm text-[var(--on-surface)] ${
                        slugAvailable === true
                          ? "focus:border-emerald-500"
                          : slugAvailable === false
                          ? "focus:border-red-500"
                          : "focus:border-[var(--primary)]"
                      }`}
                      id="orgSlug"
                      type="text"
                      placeholder="stark-academy"
                      value={orgSlug}
                      onChange={(e) => {
                        setIsSlugManuallyEdited(true);
                        setOrgSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-]+/g, ""));
                      }}
                      required
                    />
                    {slugAvailable !== null && (
                      <span className={`material-symbols-outlined absolute right-4 top-1/2 -translate-y-1/2 text-sm ${
                        slugAvailable ? "text-emerald-500" : "text-red-500"
                      }`}>
                        {slugAvailable ? "check_circle" : "cancel"}
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Org Type */}
              <div className="space-y-1">
                <label className="text-xs font-semibold text-[var(--on-surface-variant)]" htmlFor="orgType">Institution Type</label>
                <select
                  className="w-full px-5 py-3 bg-[var(--surface-container)] border-2 border-transparent focus:border-[var(--primary)] rounded-full transition-all outline-none text-sm text-[var(--on-surface)] cursor-pointer appearance-none"
                  id="orgType"
                  value={orgType}
                  onChange={(e) => setOrgType(e.target.value)}
                >
                  <option value="University">University / College</option>
                  <option value="School">School / K-12</option>
                  <option value="Coaching">Coaching / Training Center</option>
                  <option value="Company">Company / Corporate Academy</option>
                </select>
              </div>

              {/* Geographic Cascading Location (Country -> State -> City) */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {/* Country */}
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-[var(--on-surface-variant)]" htmlFor="country">Country</label>
                  <select
                    className="w-full px-4 py-3 bg-[var(--surface-container)] border border-transparent focus:border-[var(--primary)] rounded-full text-sm text-[var(--on-surface)] cursor-pointer"
                    id="country"
                    value={selectedCountry}
                    onChange={handleCountryChange}
                    required
                  >
                    <option value="">Select Country</option>
                    {countriesList.map((c) => (
                      <option key={c.isoCode} value={c.isoCode}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                </div>

                {/* State */}
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-[var(--on-surface-variant)]" htmlFor="state">State</label>
                  <select
                    className="w-full px-4 py-3 bg-[var(--surface-container)] border border-transparent focus:border-[var(--primary)] rounded-full text-sm text-[var(--on-surface)] cursor-pointer"
                    id="state"
                    value={selectedState}
                    onChange={handleStateChange}
                    required
                    disabled={!selectedCountry}
                  >
                    <option value="">Select State</option>
                    {statesList.map((s) => (
                      <option key={s.isoCode} value={s.isoCode}>
                        {s.name}
                      </option>
                    ))}
                  </select>
                </div>

                {/* City */}
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-[var(--on-surface-variant)]" htmlFor="city">City</label>
                  <select
                    className="w-full px-4 py-3 bg-[var(--surface-container)] border border-transparent focus:border-[var(--primary)] rounded-full text-sm text-[var(--on-surface)] cursor-pointer"
                    id="city"
                    value={selectedCity}
                    onChange={(e) => setSelectedCity(e.target.value)}
                    required
                    disabled={!selectedState}
                  >
                    <option value="">Select City</option>
                    {citiesList.map((ct) => (
                      <option key={ct.name} value={ct.name}>
                        {ct.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Timezone (Pre-populated from Country) */}
              <div className="space-y-1">
                <label className="text-xs font-semibold text-[var(--on-surface-variant)]" htmlFor="timezone">Timezone</label>
                <select
                  className="w-full px-5 py-3 bg-[var(--surface-container)] border-2 border-transparent focus:border-[var(--primary)] rounded-full text-sm text-[var(--on-surface)] cursor-pointer"
                  id="timezone"
                  value={selectedTimezone}
                  onChange={(e) => setSelectedTimezone(e.target.value)}
                  required
                  disabled={!selectedCountry}
                >
                  <option value="">Select Timezone</option>
                  {timezonesList.map((tz) => (
                    <option key={tz.zoneName} value={tz.zoneName}>
                      {tz.zoneName} ({tz.gmtOffsetName})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* First Workspace Section */}
            <div className="space-y-4 pt-2">
              <h3 className="text-sm font-bold uppercase tracking-wider text-[var(--primary)] border-b pb-1.5">3. Default Workspace</h3>
              <div className="space-y-1">
                <label className="text-xs font-semibold text-[var(--on-surface-variant)]" htmlFor="workspaceName">Workspace Name</label>
                <input
                  className="w-full px-5 py-3 bg-[var(--surface-container)] border-2 border-transparent focus:border-[var(--primary)] rounded-full transition-all outline-none text-sm text-[var(--on-surface)]"
                  id="workspaceName"
                  type="text"
                  placeholder="Main Workspace"
                  value={workspaceName}
                  onChange={(e) => setWorkspaceName(e.target.value)}
                  required
                />
              </div>
            </div>

            <button
              className="w-full bg-[var(--primary)] text-[var(--on-primary)] py-5 rounded-full font-headline-md hover:bg-[var(--primary-container)] active:scale-[0.98] transition-all flex items-center justify-center gap-3 mt-8 cursor-pointer shadow-md"
              type="submit"
              disabled={loading}
            >
              <span>{loading ? "Completing Setup..." : "Complete Onboarding"}</span>
              <span className="material-symbols-outlined">arrow_forward</span>
            </button>
          </form>
        </div>
      </section>
    </main>
  );
}
