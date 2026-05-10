import React from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, ShieldCheck } from 'lucide-react';
import AshokaChakra from '../components/decorative/AshokaChakra';

/**
 * Privacy.tsx — public-facing privacy policy.
 * Drafted to align with the Digital Personal Data Protection Act 2023 (DPDP Act).
 * Bilingual (English / Hindi), no auth required.
 *
 * NOTE: This is template content for the village pilot — please have your DPO
 * or legal counsel review and finalise before production deployment.
 */

const Section: React.FC<{ title: string; titleHi?: string; children: React.ReactNode }> = ({ title, titleHi, children }) => (
  <section className="space-y-2">
    <h2 className="text-lg font-semibold text-kora-100">
      {title}
      {titleHi && <span className="block font-devanagari text-sm text-slate-400/70 font-normal mt-0.5">{titleHi}</span>}
    </h2>
    <div className="text-sm text-slate-300/85 leading-relaxed space-y-2">{children}</div>
  </section>
);

const Privacy: React.FC = () => {
  return (
    <div className="min-h-screen bg-[#060B18] text-slate-200">
      {/* Background mesh */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="aurora-orb w-[600px] h-[600px] bg-[#0D92F4]/10 top-[-10%] left-[-10%]" />
        <div className="aurora-orb w-[400px] h-[400px] bg-[#77CDFF]/8 bottom-[-15%] right-[-5%]" style={{ animationDelay: '-7s' }} />
        <div className="absolute inset-0 grain-overlay" />
      </div>

      <div className="relative z-10 max-w-3xl mx-auto px-5 py-10 sm:py-14">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <Link to="/" className="inline-flex items-center gap-1.5 text-sm text-slate-400 hover:text-[#77CDFF] transition-colors mb-6">
            <ArrowLeft className="w-4 h-4" />
            Back to home
          </Link>

          <header className="mb-10 pb-6 border-b border-white/[0.06]">
            <div className="flex items-center gap-3 mb-3">
              <AshokaChakra size={36} />
              <ShieldCheck className="w-5 h-5 text-[#77CDFF]" />
            </div>
            <h1 className="text-3xl sm:text-4xl font-display font-bold text-gradient-gold mb-1">Privacy Policy</h1>
            <p className="font-devanagari text-lg text-slate-400/70">गोपनीयता नीति</p>
            <p className="text-xs text-slate-500 mt-3">Last updated: 7 May 2026</p>
          </header>

          <div className="space-y-8">
            <Section title="Data Fiduciary" titleHi="डेटा न्यासी">
              <p>
                NyayaSetu (न्यायसेतु) is operated as a citizen-governance pilot. The data fiduciary
                under the Digital Personal Data Protection Act, 2023 is the project owner identified
                in the Contact section below. By using this service you provide your consent under
                Section 6 of the DPDP Act for the purposes set out below.
              </p>
            </Section>

            <Section title="What Data We Collect" titleHi="हम कौन सा डेटा एकत्र करते हैं">
              <ul className="list-disc pl-5 space-y-1">
                <li>Account: name, username, email, phone number, role.</li>
                <li>Location: city / district as provided during registration.</li>
                <li>Grievance content: title, description, attached documents and images.</li>
                <li>Voice recordings: only when you explicitly use the NyayaVaani voice features. Audio is processed for transcription, then discarded unless you submit it as part of a grievance.</li>
                <li>Usage logs: timestamps, IP address, device type — used for security and audit only.</li>
                <li>Authentication tokens: stored in your browser's local storage to keep you signed in.</li>
              </ul>
            </Section>

            <Section title="Why We Process This Data" titleHi="हम यह डेटा क्यों संसाधित करते हैं">
              <ul className="list-disc pl-5 space-y-1">
                <li>To deliver, route and resolve your grievances to the relevant department.</li>
                <li>To match you with eligible government welfare schemes.</li>
                <li>To draft and deliver official notices to you when applicable.</li>
                <li>To prevent abuse, fraud and unauthorised access.</li>
                <li>To comply with applicable Indian law and lawful government requests.</li>
              </ul>
            </Section>

            <Section title="Retention" titleHi="अवधारण">
              <p>
                Grievance records and associated evidence are retained for three (3) years after
                resolution, after which they are anonymised or deleted in accordance with departmental
                record-keeping policies. Voice recordings are deleted within 30 days of processing
                unless attached to a grievance.
              </p>
            </Section>

            <Section title="Your Rights" titleHi="आपके अधिकार">
              <ul className="list-disc pl-5 space-y-1">
                <li><strong>Access</strong> — request a copy of your personal data.</li>
                <li><strong>Correction</strong> — request correction of inaccurate data.</li>
                <li><strong>Erasure</strong> — request deletion when the lawful purpose has ended.</li>
                <li><strong>Grievance</strong> — file a complaint with our Data Protection Officer (below) or the Data Protection Board of India.</li>
                <li><strong>Withdrawal</strong> — withdraw consent for non-essential processing at any time.</li>
              </ul>
            </Section>

            <Section title="Cookies &amp; Local Storage" titleHi="कुकीज़ और स्थानीय भंडारण">
              <p>
                We use a JSON Web Token (JWT) stored in your browser's local storage for session
                authentication. We do not use third-party advertising or tracking cookies. Session
                tokens expire automatically and can be revoked by you from the Settings page.
              </p>
            </Section>

            <Section title="Sharing With Third Parties" titleHi="तीसरे पक्ष के साथ साझा करना">
              <p>
                We do not sell your data. We share grievance content only with the relevant
                government department for resolution. AI processing (transcription, summarisation,
                translation) may be performed by third-party model providers under data-processing
                agreements, with content limited to what is necessary for the requested service.
              </p>
            </Section>

            <Section title="Security" titleHi="सुरक्षा">
              <p>
                Passwords are hashed with bcrypt. Communication uses HTTPS in production. Database
                access is role-restricted and audit-logged. Despite our safeguards, no online service
                is fully secure — please report any suspected vulnerability to the contact below.
              </p>
            </Section>

            <Section title="Contact" titleHi="संपर्क">
              <p>
                For privacy questions, requests under your DPDP Act rights, or to file a data-protection
                grievance, write to <a className="text-[#77CDFF] hover:underline" href="mailto:privacy@nyayasetu.in">privacy@nyayasetu.in</a>.
                We aim to respond within 30 days.
              </p>
            </Section>

            <Section title="Updates to This Policy" titleHi="इस नीति में अद्यतन">
              <p>
                We will update this page when our practices change. Material changes will be
                announced on the application home screen.
              </p>
            </Section>
          </div>

          <footer className="mt-12 pt-6 border-t border-white/[0.06] flex flex-wrap gap-4 text-xs text-slate-500">
            <Link to="/terms" className="hover:text-[#77CDFF] transition-colors">Terms of Service</Link>
            <Link to="/login" className="hover:text-[#77CDFF] transition-colors">Login</Link>
            <Link to="/public/schemes" className="hover:text-[#77CDFF] transition-colors">Browse Schemes</Link>
            <span className="ml-auto">NyayaSetu &middot; पायलट परिनियोजन</span>
          </footer>
        </motion.div>
      </div>
    </div>
  );
};

export default Privacy;
