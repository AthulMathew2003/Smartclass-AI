"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Country, State, City } from "country-state-city";
import { getMemoryAccessToken, API_BASE_URL, fetchCurrentUser } from "../../../lib/auth";

// ── Shared field token ────────────────────────────────────────
const inputCls = "ds-input";
const labelCls = "block text-xs font-semibold mb-1.5";

function FieldLabel({ htmlFor, children }: { htmlFor: string; children: React.ReactNode }) {
  return (
    <label htmlFor={htmlFor} className={labelCls} style={{ color: "var(--on-surface-variant)" }}>
      {children}
    </label>
  );
}

function SectionHeading({ number, title, subtitle }: { number: string; title: string; subtitle?: string }) {
  return (
    <div className="flex items-start gap-4 mb-5">
      <div className="w-8 h-8 rounded-xl flex items-center justify-center text-xs font-bold shrink-0 mt-0.5" style={{ backgroundColor: "var(--tertiary-fixed)", color: "var(--on-tertiary-fixed)" }}>
        {number}
      </div>
      <div>
        <h3 className="text-sm font-bold" style={{ color: "var(--on-surface)" }}>{title}</h3>
        {subtitle && <p className="text-xs mt-0.5" style={{ color: "var(--on-surface-variant)" }}>{subtitle}</p>}
      </div>
    </div>
  );
}

export default function CompleteRegistrationPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [checkingAuth, setCheckingAuth] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Owner details
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [phone, setPhone] = useState("");

  // Org details
  const [orgName, setOrgName] = useState("");
  const [orgSlug, setOrgSlug] = useState("");
  const [isSlugManuallyEdited, setIsSlugManuallyEdited] = useState(false);
  const [orgType, setOrgType] = useState("University");
  const [selectedCountry, setSelectedCountry] = useState("");
  const [selectedState, setSelectedState] = useState("");
  const [selectedCity, setSelectedCity] = useState("");
  const [selectedTimezone, setSelectedTimezone] = useState("");
  const [orgDescription, setOrgDescription] = useState("");

  // Workspace
  const [workspaceName, setWorkspaceName] = useState("Main Workspace");

  // Availability
  const [nameAvailable, setNameAvailable] = useState<boolean | null>(null);
  const [slugAvailable, setSlugAvailable] = useState<boolean | null>(null);

  // Geo data
  const [countriesList, setCountriesList] = useState<any[]>([]);
  const [statesList, setStatesList] = useState<any[]>([]);
  const [citiesList, setCitiesList] = useState<any[]>([]);
  const [timezonesList, setTimezonesList] = useState<any[]>([]);

  const slugify = (text: string) =>
    text.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)+/g, "");

  useEffect(() => {
    const checkAuth = async () => {
      const token = getMemoryAccessToken();
      const user = await fetchCurrentUser();
      if (!token || !user) { router.replace("/login"); return; }
      if (user.first_name) setFirstName(user.first_name);
      if (user.last_name) setLastName(user.last_name);
      setCheckingAuth(false);
    };
    checkAuth();
    setCountriesList(Country.getAllCountries());
  }, [router]);

  const handleCountryChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const code = e.target.value;
    setSelectedCountry(code);
    setSelectedState(""); setSelectedCity(""); setSelectedTimezone(""); setCitiesList([]);
    if (code) {
      setStatesList(State.getStatesOfCountry(code));
      const country = Country.getCountryByCode(code);
      if (country?.timezones) {
        setTimezonesList(country.timezones);
        if (country.timezones.length > 0) setSelectedTimezone(country.timezones[0].zoneName);
      } else setTimezonesList([]);
    } else { setStatesList([]); setTimezonesList([]); }
  };

  const handleStateChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const code = e.target.value;
    setSelectedState(code); setSelectedCity("");
    if (selectedCountry && code) setCitiesList(City.getCitiesOfState(selectedCountry, code));
    else setCitiesList([]);
  };

  // Name availability
  useEffect(() => {
    if (!orgName.trim()) { setNameAvailable(null); return; }
    const t = setTimeout(async () => {
      try {
        const r = await fetch(`${API_BASE_URL}/organizations/check-name?name=${encodeURIComponent(orgName)}`);
        if (r.ok) setNameAvailable((await r.json()).available);
      } catch {}
    }, 450);
    return () => clearTimeout(t);
  }, [orgName]);

  // Slug availability
  useEffect(() => {
    if (!orgSlug.trim()) { setSlugAvailable(null); return; }
    const t = setTimeout(async () => {
      try {
        const r = await fetch(`${API_BASE_URL}/organizations/check-slug?slug=${encodeURIComponent(orgSlug)}`);
        if (r.ok) setSlugAvailable((await r.json()).available);
      } catch {}
    }, 450);
    return () => clearTimeout(t);
  }, [orgSlug]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (nameAvailable === false) { setError("Organization name is already taken."); return; }
    if (slugAvailable === false) { setError("URL Slug is already taken."); return; }
    setLoading(true);
    try {
      const token = getMemoryAccessToken();
      const countryName = Country.getCountryByCode(selectedCountry)?.name || selectedCountry;
      const stateName = State.getStateByCodeAndCountry(selectedState, selectedCountry)?.name || selectedState;
      const payload = { org_name: orgName, org_slug: orgSlug, org_type: orgType, org_country: countryName, org_state: stateName, org_city: selectedCity, org_timezone: selectedTimezone, org_description: orgDescription, owner_first_name: firstName, owner_last_name: lastName, owner_phone: phone || null, workspace_name: workspaceName };
      const res = await fetch(`${API_BASE_URL}/organizations/onboarding`, { method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` }, body: JSON.stringify(payload) });
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail?.message || "Failed to complete onboarding."); }
      router.replace("/classroom");
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred during onboarding.");
    } finally {
      setLoading(false);
    }
  };

  if (checkingAuth) {
    return (
      <div className="min-h-screen bg-[var(--background)] flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-t-transparent rounded-full animate-spin" style={{ borderColor: "var(--primary)", borderTopColor: "transparent" }} />
      </div>
    );
  }

  const selectCls = `${inputCls} cursor-pointer appearance-none`;

  return (
    <main className="min-h-screen flex bg-[var(--background)] text-[var(--on-surface)]">
      {/* ── Left Panel ─────────────────────────────────────── */}
      <section className="hidden lg:flex w-[40%] bg-[var(--primary)] relative overflow-hidden flex-col justify-between p-14">
        <svg className="absolute -top-32 -right-32 w-[420px] h-[420px] opacity-10 pointer-events-none" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
          <path d="M44.7,-76.4C58.1,-69.2,69.2,-58.1,76.4,-44.7C83.6,-31.3,86.9,-15.7,85.2,-0.9C83.6,13.8,77,27.7,69.1,40.4C61.2,53,52.1,64.3,40.5,72.4C28.8,80.5,14.4,85.4,-0.6,86.4C-15.6,87.4,-31.1,84.4,-44.8,77.3C-58.4,70.2,-70.2,59,-77.3,45.4C-84.4,31.7,-86.7,15.9,-86.1,0.4C-85.4,-15.1,-81.8,-30.2,-74.1,-43.3C-66.5,-56.3,-54.9,-67.2,-41.4,-74.3C-27.9,-81.4,-14,-84.7,0.4,-85.4C14.7,-86.1,29.4,-84.1,44.7,-76.4Z" fill="white" transform="translate(100 100)" />
        </svg>

        <div className="flex items-center gap-3 relative z-10">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center font-bold text-sm" style={{ backgroundColor: "var(--tertiary-fixed)", color: "var(--on-tertiary-fixed)" }}>S</div>
          <span className="text-lg font-bold text-white">SmartClass AI</span>
        </div>

        <div className="relative z-10 space-y-8">
          <div className="space-y-4">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider" style={{ backgroundColor: "rgba(195,241,133,0.15)", color: "var(--tertiary-fixed)" }}>
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--tertiary-fixed)] animate-pulse" />
              Step 2 of 2
            </div>
            <h1 className="text-3xl font-bold leading-tight text-white">
              Complete your<br />institutional<br />setup.
            </h1>
            <p className="text-sm leading-relaxed" style={{ color: "rgba(255,255,255,0.65)" }}>
              Define your organization, invite your team, and launch your first workspace.
            </p>
          </div>

          <div className="space-y-3">
            {[
              { icon: "check_circle", text: "Single-tenant workspace, isolated transactionally" },
              { icon: "check_circle", text: "Auto-generated Owner and Admin permissions" },
              { icon: "check_circle", text: "Immediately invite teachers and students" },
            ].map((item, i) => (
              <div key={i} className="flex items-center gap-3">
                <span className="material-symbols-outlined text-[18px] shrink-0" style={{ color: "var(--tertiary-fixed)" }}>{item.icon}</span>
                <span className="text-sm" style={{ color: "rgba(255,255,255,0.8)" }}>{item.text}</span>
              </div>
            ))}
          </div>
        </div>

        <p className="text-xs font-semibold relative z-10" style={{ color: "rgba(255,255,255,0.35)" }}>© 2024 SmartClass AI</p>
      </section>

      {/* ── Right Panel: Form ─────────────────────────────── */}
      <section className="flex-1 overflow-y-auto flex items-start justify-center p-6 md:p-10">
        <div className="w-full max-w-2xl animate-slide-up py-6">
          {/* Mobile brand */}
          <div className="flex items-center gap-2 mb-6 lg:hidden">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center font-bold text-xs" style={{ backgroundColor: "var(--primary)", color: "var(--on-primary)" }}>S</div>
            <span className="text-base font-bold">SmartClass AI</span>
          </div>

          <div className="mb-8">
            <div className="flex items-center gap-2 mb-3">
              <span className="w-6 h-0.5 rounded-full" style={{ backgroundColor: "var(--secondary-container)" }} />
              <span className="text-xs font-bold uppercase tracking-widest" style={{ color: "var(--secondary)" }}>Step 2 of 2</span>
            </div>
            <h2 className="text-2xl font-bold tracking-tight" style={{ color: "var(--on-surface)" }}>Set Up Your Organization</h2>
            <p className="text-sm mt-1.5" style={{ color: "var(--on-surface-variant)" }}>Build your brand-new digital academy space.</p>
          </div>

          {error && (
            <div className="mb-6 p-4 rounded-xl flex items-center gap-2.5 text-sm font-medium animate-fade-in" style={{ backgroundColor: "rgba(186,26,26,0.06)", border: "1px solid rgba(186,26,26,0.2)", color: "#ba1a1a" }}>
              <span className="material-symbols-outlined text-[18px]">error</span>
              <span>{error}</span>
            </div>
          )}

          <form className="space-y-8" onSubmit={handleSubmit}>
            {/* ── Section 1: Owner Profile ──────────────────── */}
            <div className="ds-card space-y-5">
              <SectionHeading number="1" title="Owner Profile" subtitle="Your name as it appears in the organization." />
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <FieldLabel htmlFor="firstName">First Name</FieldLabel>
                  <input id="firstName" type="text" className={inputCls} value={firstName} onChange={(e) => setFirstName(e.target.value)} required />
                </div>
                <div>
                  <FieldLabel htmlFor="lastName">Last Name</FieldLabel>
                  <input id="lastName" type="text" className={inputCls} value={lastName} onChange={(e) => setLastName(e.target.value)} required />
                </div>
              </div>
              <div>
                <FieldLabel htmlFor="phone">Contact Number <span style={{ color: "var(--on-surface-variant)", fontWeight: 400 }}>(optional)</span></FieldLabel>
                <input id="phone" type="text" className={inputCls} placeholder="+1 (555) 019-2834" value={phone} onChange={(e) => setPhone(e.target.value)} />
              </div>
            </div>

            {/* ── Section 2: Organization Details ──────────── */}
            <div className="ds-card space-y-5">
              <SectionHeading number="2" title="Organization Details" subtitle="These details identify your institution on SmartClass AI." />

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <FieldLabel htmlFor="orgName">Organization Name</FieldLabel>
                  <div className="relative">
                    <input
                      id="orgName" type="text" className={inputCls} placeholder="Stark Academy"
                      value={orgName}
                      onChange={(e) => { const v = e.target.value; setOrgName(v); if (!isSlugManuallyEdited) setOrgSlug(slugify(v)); }}
                      required
                    />
                    {nameAvailable !== null && (
                      <span className={`material-symbols-outlined absolute right-4 top-1/2 -translate-y-1/2 text-[18px] ${nameAvailable ? "text-emerald-500" : "text-red-500"}`}>
                        {nameAvailable ? "check_circle" : "cancel"}
                      </span>
                    )}
                  </div>
                </div>
                <div>
                  <FieldLabel htmlFor="orgSlug">URL Slug</FieldLabel>
                  <div className="relative">
                    <input
                      id="orgSlug" type="text" className={inputCls} placeholder="stark-academy"
                      value={orgSlug}
                      onChange={(e) => { setIsSlugManuallyEdited(true); setOrgSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-]+/g, "")); }}
                      required
                    />
                    {slugAvailable !== null && (
                      <span className={`material-symbols-outlined absolute right-4 top-1/2 -translate-y-1/2 text-[18px] ${slugAvailable ? "text-emerald-500" : "text-red-500"}`}>
                        {slugAvailable ? "check_circle" : "cancel"}
                      </span>
                    )}
                  </div>
                </div>
              </div>

              <div>
                <FieldLabel htmlFor="orgType">Institution Type</FieldLabel>
                <select id="orgType" className={selectCls} value={orgType} onChange={(e) => setOrgType(e.target.value)}>
                  <option value="University">University / College</option>
                  <option value="School">School / K-12</option>
                  <option value="Coaching">Coaching / Training Center</option>
                  <option value="Company">Company / Corporate Academy</option>
                </select>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <FieldLabel htmlFor="country">Country</FieldLabel>
                  <select id="country" className={selectCls} value={selectedCountry} onChange={handleCountryChange} required>
                    <option value="">Select Country</option>
                    {countriesList.map((c) => <option key={c.isoCode} value={c.isoCode}>{c.name}</option>)}
                  </select>
                </div>
                <div>
                  <FieldLabel htmlFor="state">State</FieldLabel>
                  <select id="state" className={selectCls} value={selectedState} onChange={handleStateChange} disabled={!selectedCountry} required>
                    <option value="">Select State</option>
                    {statesList.map((s) => <option key={s.isoCode} value={s.isoCode}>{s.name}</option>)}
                  </select>
                </div>
                <div>
                  <FieldLabel htmlFor="city">City</FieldLabel>
                  <select id="city" className={selectCls} value={selectedCity} onChange={(e) => setSelectedCity(e.target.value)} disabled={!selectedState} required>
                    <option value="">Select City</option>
                    {citiesList.map((ct) => <option key={ct.name} value={ct.name}>{ct.name}</option>)}
                  </select>
                </div>
              </div>

              <div>
                <FieldLabel htmlFor="timezone">Timezone</FieldLabel>
                <select id="timezone" className={selectCls} value={selectedTimezone} onChange={(e) => setSelectedTimezone(e.target.value)} disabled={!selectedCountry} required>
                  <option value="">Select Timezone</option>
                  {timezonesList.map((tz) => <option key={tz.zoneName} value={tz.zoneName}>{tz.zoneName} ({tz.gmtOffsetName})</option>)}
                </select>
              </div>
            </div>

            {/* ── Section 3: Default Workspace ─────────────── */}
            <div className="ds-card space-y-4">
              <SectionHeading number="3" title="Default Workspace" subtitle="Your first workspace where members will be assigned." />
              <div>
                <FieldLabel htmlFor="workspaceName">Workspace Name</FieldLabel>
                <input id="workspaceName" type="text" className={inputCls} placeholder="Main Workspace" value={workspaceName} onChange={(e) => setWorkspaceName(e.target.value)} required />
              </div>
            </div>

            <button type="submit" disabled={loading} className="ds-btn-primary w-full py-4 text-base">
              {loading ? (
                <><span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />Completing Setup...</>
              ) : (
                <>Complete Onboarding <span className="material-symbols-outlined text-[18px]">arrow_forward</span></>
              )}
            </button>
          </form>
        </div>
      </section>
    </main>
  );
}
