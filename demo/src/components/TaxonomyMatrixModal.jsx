import { useState, useEffect } from 'react'
import { createPortal } from 'react-dom'

export const PII_TAXONOMY_26 = [
  {
    id: 'PERSON',
    name: 'Person Name',
    category: 'Identity',
    risk: 'High',
    riskColor: 'text-amber-400 border-amber-500/30 bg-amber-500/10',
    description: 'First, middle, and last names identified via phonetic & multilingual entity corpus.',
    sample: 'Saikalyan Chandran Bose',
    method: 'Known corpus + phonetic vowel-consonant heuristic'
  },
  {
    id: 'EMAIL',
    name: 'Email Address',
    category: 'Communication',
    risk: 'High',
    riskColor: 'text-amber-400 border-amber-500/30 bg-amber-500/10',
    description: 'Corporate and personal email addresses compliant with RFC 5322.',
    sample: 'judge.sih2024@domain.org',
    method: 'RFC 5322 regex + TLD validation'
  },
  {
    id: 'PHONE',
    name: 'Phone Number',
    category: 'Communication',
    risk: 'High',
    riskColor: 'text-amber-400 border-amber-500/30 bg-amber-500/10',
    description: 'Mobile & landline numbers with international and domestic (+91) dialing formats.',
    sample: '+91 98765 43210',
    method: 'E.164 + Indian telecommunication series prefix'
  },
  {
    id: 'ADDRESS',
    name: 'Address & Precise GPS Location',
    category: 'Location',
    risk: 'Critical',
    riskColor: 'text-rose-400 border-rose-500/30 bg-rose-500/10',
    description: 'Physical postal addresses, street landmarks, and decimal GPS latitude/longitude coordinates.',
    sample: '12.9716, 77.5946',
    method: 'GPS coordinate bounds check + locality keywords'
  },
  {
    id: 'PASSWORD',
    name: 'Password, Passcode & PIN',
    category: 'Credentials',
    risk: 'Critical',
    riskColor: 'text-rose-400 border-rose-500/30 bg-rose-500/10',
    description: 'Master passwords, PINs, MPINs, vault passphrases, and security answers.',
    sample: 'SuperSecretBankPass2026!',
    method: 'Entropy scoring (charset mix) + security keywords'
  },
  {
    id: 'OTP',
    name: 'One-Time Password (2FA)',
    category: 'Credentials',
    risk: 'Critical',
    riskColor: 'text-rose-400 border-rose-500/30 bg-rose-500/10',
    description: 'Short-lived 4 to 8 digit authentication and verification codes displayed in browser/SMS.',
    sample: 'OTP: 839201',
    method: 'Temporal token heuristic + 2FA label context'
  },
  {
    id: 'CREDIT_CARD',
    name: 'Credit Card Number',
    category: 'Financial',
    risk: 'Critical',
    riskColor: 'text-rose-400 border-rose-500/30 bg-rose-500/10',
    description: 'Visa, Mastercard, RuPay, Amex card numbers with mathematical checksum validation.',
    sample: '4111 1111 1111 1111',
    method: 'ISO/IEC 7810 format + Luhn algorithm (mod-10)'
  },
  {
    id: 'DEBIT_CARD',
    name: 'Debit Card Number',
    category: 'Financial',
    risk: 'Critical',
    riskColor: 'text-rose-400 border-rose-500/30 bg-rose-500/10',
    description: 'Direct account debit card numbers verified against banking card ranges.',
    sample: '4532 0151 1283 0366',
    method: 'BIN identification + Luhn verification'
  },
  {
    id: 'BANK_ACCOUNT',
    name: 'Bank Account Number',
    category: 'Financial',
    risk: 'Critical',
    riskColor: 'text-rose-400 border-rose-500/30 bg-rose-500/10',
    description: 'Core banking customer account numbers (9 to 18 digits) appearing in tables or inputs.',
    sample: '98765432109876',
    method: 'Length + digit distribution + banking context'
  },
  {
    id: 'IFSC',
    name: 'IFSC Code',
    category: 'Financial',
    risk: 'Medium',
    riskColor: 'text-cyan-400 border-cyan-500/30 bg-cyan-500/10',
    description: 'Reserve Bank of India 11-character alpha-numeric bank branch routing codes.',
    sample: 'SBIN0001234',
    method: 'RBI regex (4 letters + 0 + 6 alphanumeric)'
  },
  {
    id: 'UPI_ID',
    name: 'UPI ID / VPA',
    category: 'Financial',
    risk: 'High',
    riskColor: 'text-amber-400 border-amber-500/30 bg-amber-500/10',
    description: 'Unified Payments Interface Virtual Payment Addresses (@oksbi, @paytm, @ybl, etc.).',
    sample: 'saikalyancb@oksbi',
    method: 'NPCI VPA format (handle@psp without TLD)'
  },
  {
    id: 'AADHAAR',
    name: 'Aadhaar Number',
    category: 'Government ID',
    risk: 'Critical',
    riskColor: 'text-rose-400 border-rose-500/30 bg-rose-500/10',
    description: 'Unique Identification Authority of India (UIDAI) 12-digit biometric identity numbers.',
    sample: '2345 6789 1238',
    method: 'Dihedral Group D5 Verhoeff checksum algorithm'
  },
  {
    id: 'PAN',
    name: 'Permanent Account Number (PAN)',
    category: 'Government ID',
    risk: 'High',
    riskColor: 'text-amber-400 border-amber-500/30 bg-amber-500/10',
    description: 'Indian Income Tax Department 10-character alphanumeric taxpayer ID.',
    sample: 'ABCDE1234F',
    method: '5 letters + 4 digits + 1 letter structure'
  },
  {
    id: 'PASSPORT',
    name: 'Passport Number',
    category: 'Government ID',
    risk: 'Critical',
    riskColor: 'text-rose-400 border-rose-500/30 bg-rose-500/10',
    description: 'International travel document numbers with standard country prefixes.',
    sample: 'Z1234567',
    method: 'Letter + 7 digits regex pattern'
  },
  {
    id: 'DRIVERS_LICENSE',
    name: 'Driving Licence',
    category: 'Government ID',
    risk: 'High',
    riskColor: 'text-amber-400 border-amber-500/30 bg-amber-500/10',
    description: 'Indian regional transport department driving license numbers (State Code + Year + ID).',
    sample: 'KA01 2011 0012345',
    method: 'RTO format (SS-RR-YYYY-NNNNNNN)'
  },
  {
    id: 'DATE_OF_BIRTH',
    name: 'Date of Birth',
    category: 'Identity',
    risk: 'Medium',
    riskColor: 'text-cyan-400 border-cyan-500/30 bg-cyan-500/10',
    description: 'Personal birth dates in DD/MM/YYYY, ISO 8601, and alphanumeric month formats.',
    sample: '15/08/1998',
    method: 'Date validation + historical year bounds (1900–2026)'
  },
  {
    id: 'FINANCIAL_VALUE',
    name: 'Financial Value & Balance',
    category: 'Financial',
    risk: 'High',
    riskColor: 'text-amber-400 border-amber-500/30 bg-amber-500/10',
    description: 'Account balances, transaction amounts, and currency-denominated compensation values.',
    sample: 'Account Balance: ₹85,400',
    method: 'Currency symbols (₹, $, €, £) + balance keyword context'
  },
  {
    id: 'API_KEY',
    name: 'Developer API Key',
    category: 'Secrets',
    risk: 'Critical',
    riskColor: 'text-rose-400 border-rose-500/30 bg-rose-500/10',
    description: 'Cloud provider and SaaS secret keys: OpenAI (sk-proj-*), GitHub, AWS, Slack, npm.',
    sample: 'sk-proj-abc12345678901234567890',
    method: 'Provider prefix matching + Shannon entropy verification'
  },
  {
    id: 'ACCESS_TOKEN',
    name: 'Session Token & Bearer Credential',
    category: 'Secrets',
    risk: 'Critical',
    riskColor: 'text-rose-400 border-rose-500/30 bg-rose-500/10',
    description: 'Bearer tokens, session cookies (PHPSESSID, connect.sid), and CSRF tokens.',
    sample: 'Bearer eyJhbGciOiJIUzI1NiJ9.sih.demo',
    method: 'Auth header parsing + session identifier signatures'
  },
  {
    id: 'JWT',
    name: 'JSON Web Token (JWT)',
    category: 'Secrets',
    risk: 'Critical',
    riskColor: 'text-rose-400 border-rose-500/30 bg-rose-500/10',
    description: 'Base64URL-encoded identity and authorization tokens containing claims payload.',
    sample: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.signature',
    method: 'Three-segment base64url structure regex'
  },
  {
    id: 'SECRET',
    name: 'SSH Key, .env & DB Secrets',
    category: 'Secrets',
    risk: 'Critical',
    riskColor: 'text-rose-400 border-rose-500/30 bg-rose-500/10',
    description: 'PEM private keys (RSA/EC), database connection URIs, client secrets, and .env tokens.',
    sample: '-----BEGIN RSA PRIVATE KEY-----',
    method: 'PEM headers + DB URI schemes (mongodb, postgres, redis)'
  },
  {
    id: 'PRIVATE_MESSAGE',
    name: 'Private Message & Medical Data',
    category: 'Communication',
    risk: 'High',
    riskColor: 'text-amber-400 border-amber-500/30 bg-amber-500/10',
    description: 'Clinical consultation notes, patient prescriptions, support tickets, and confidential comms.',
    sample: 'Patient diagnosis: acute bronchitis',
    method: 'Clinical ontology + corporate confidentiality markers'
  },
  {
    id: 'FACE',
    name: 'Biometric Identifiers',
    category: 'Biometrics',
    risk: 'Critical',
    riskColor: 'text-rose-400 border-rose-500/30 bg-rose-500/10',
    description: 'Fingerprint mentions, retina/iris scans, Face ID references, and biometric credentials.',
    sample: 'Fingerprint scan verified',
    method: 'Biometric keyword lexicons + visual layout features'
  },
  {
    id: 'QR_CODE',
    name: 'Auth, WiFi & Payment QR Data',
    category: 'Credentials',
    risk: 'High',
    riskColor: 'text-amber-400 border-amber-500/30 bg-amber-500/10',
    description: '2FA authenticator URIs (otpauth://), WiFi connection strings, and payment QR codes.',
    sample: 'otpauth://totp/Vault:user?secret=JBSWY3DPEHPK3PXP',
    method: 'URI scheme detection (otpauth, WIFI, bitcoin, upi)'
  },
  {
    id: 'USERNAME',
    name: 'User Handle / Account Login',
    category: 'Identity',
    risk: 'Medium',
    riskColor: 'text-cyan-400 border-cyan-500/30 bg-cyan-500/10',
    description: 'Social handles (@handle), profile usernames, and explicit login account identifiers.',
    sample: '@saikalyan_dev',
    method: '@handle prefix + username label heuristics'
  },
  {
    id: 'OTHER_IDENTIFIER',
    name: 'IP Address & Device/Voter ID',
    category: 'System',
    risk: 'Medium',
    riskColor: 'text-cyan-400 border-cyan-500/30 bg-cyan-500/10',
    description: 'IPv4 & IPv6 addresses, device hardware IDs, employee badges, customer IDs, and Voter IDs.',
    sample: '192.168.1.104',
    method: 'IPv4 octet range (0-255) + IPv6 + structured ID prefixes'
  }
]

export default function TaxonomyMatrixModal({ isOpen, onClose, onInjectSample }) {
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('All')
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  useEffect(() => {
    if (!isOpen) return
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose])

  if (!isOpen || !mounted) return null

  const categories = ['All', 'Financial', 'Credentials', 'Secrets', 'Government ID', 'Location', 'Communication', 'Identity', 'Biometrics', 'System']

  const filtered = PII_TAXONOMY_26.filter(item => {
    const matchesSearch = item.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          item.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          item.sample.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          item.id.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesCat = selectedCategory === 'All' || item.category === selectedCategory
    return matchesSearch && matchesCat
  })

  const scrollToStats = () => {
    onClose()
    const el = document.getElementById('statistics')
    if (el) el.scrollIntoView({ behavior: 'smooth' })
  }

  const modalJSX = (
    <div 
      className="fixed inset-0 z-[99999] flex items-center justify-center p-3 sm:p-5 bg-black/80 backdrop-blur-md"
      onClick={onClose}
    >
      <div 
        className="relative w-full max-w-4xl max-h-[90vh] bg-[#0c1328] border border-cyan-500/40 rounded-2xl shadow-[0_0_60px_rgba(6,182,212,0.35)] flex flex-col overflow-hidden text-white"
        onClick={(e) => e.stopPropagation()}
      >
        
        {/* Header */}
        <div className="p-4 sm:p-5 border-b border-white/10 flex items-center justify-between bg-[#080d1c] flex-shrink-0">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xl">🛡️</span>
              <h3 className="text-base sm:text-lg font-black text-white tracking-tight">
                Visiionary 26-Category Privacy Matrix
              </h3>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-400/30 font-mono">
                SIH Taxonomy Complete
              </span>
            </div>
            <p className="text-xs text-gray-400 mt-1">
              Complete on-device perception taxonomy covering visual UI landmarks, credentials, financial records, and network identifiers. Click any row to test live.
            </p>
          </div>

          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-gray-400 hover:text-white flex items-center justify-center text-sm font-bold transition-all cursor-pointer"
          >
            ✕
          </button>
        </div>

        {/* Filter & Search Bar */}
        <div className="p-3 sm:p-4 border-b border-white/5 bg-[#091024] space-y-2.5 flex-shrink-0">
          <div className="flex flex-col sm:flex-row items-center gap-2.5">
            <div className="relative flex-1 w-full">
              <span className="absolute left-3 top-2.5 text-gray-500 text-xs">🔍</span>
              <input
                type="text"
                placeholder="Search categories (e.g. GPS, Bearer, SSH, Aadhaar, IP)..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-8 pr-3 py-1.5 rounded-lg bg-black/50 border border-white/10 text-xs text-white placeholder-gray-500 outline-none focus:border-cyan-400"
              />
            </div>
            <span className="text-[11px] text-gray-400 font-mono whitespace-nowrap self-end sm:self-center">
              Showing {filtered.length} of 26 Categories
            </span>
          </div>

          {/* Category Chips */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-[11px]">
            {categories.map(cat => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`px-2.5 py-1 rounded-md font-semibold whitespace-nowrap transition-all cursor-pointer ${
                  selectedCategory === cat
                    ? 'bg-cyan-600 text-white shadow-[0_0_10px_rgba(6,182,212,0.3)]'
                    : 'bg-white/5 text-gray-400 hover:text-white hover:bg-white/10'
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>

        {/* Categories Table / List */}
        <div className="flex-1 overflow-y-auto p-3 sm:p-4 space-y-2.5 divide-y divide-white/5">
          {filtered.map(item => (
            <div
              key={item.id}
              className="pt-2.5 first:pt-0 flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 rounded-xl bg-white/[0.02] hover:bg-white/[0.05] border border-transparent hover:border-white/10 transition-all"
            >
              <div className="space-y-1 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs font-bold text-white">{item.name}</span>
                  <span className="px-1.5 py-0.5 rounded text-[10px] font-mono text-cyan-300 bg-cyan-950/60 border border-cyan-500/20">
                    {item.id}
                  </span>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${item.riskColor}`}>
                    {item.risk} Risk
                  </span>
                  <span className="text-[10px] text-gray-500">· {item.category}</span>
                </div>

                <p className="text-[11px] text-gray-400 leading-relaxed">
                  {item.description}
                </p>

                <div className="flex items-center gap-2 text-[10px] text-gray-500 font-mono">
                  <span>Engine:</span>
                  <span className="text-gray-300">{item.method}</span>
                </div>
              </div>

              {/* Sample & Injection Action */}
              <div className="flex sm:flex-col items-center sm:items-end justify-between gap-2 flex-shrink-0">
                <div className="px-2 py-1 rounded bg-black/60 border border-white/10 font-mono text-[11px] text-emerald-300 max-w-[200px] truncate" title={item.sample}>
                  {item.sample}
                </div>
                <button
                  onClick={() => {
                    onInjectSample(item.sample)
                    onClose()
                  }}
                  className="px-3 py-1 rounded-lg bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white text-[11px] font-bold shadow-[0_0_10px_rgba(6,182,212,0.3)] transition-all cursor-pointer flex items-center gap-1"
                >
                  <span>⚡</span>
                  <span>Test in Sandbox</span>
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="p-3 border-t border-white/10 bg-[#080d1c] flex flex-wrap items-center justify-between gap-2 text-xs text-gray-400 flex-shrink-0">
          <button
            onClick={scrollToStats}
            className="text-xs text-cyan-300 hover:text-cyan-200 font-semibold flex items-center gap-1 cursor-pointer"
          >
            <span>📊</span>
            <span>View Full 26-Class Empirical Stats Table ↓</span>
          </button>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-white/10 hover:bg-white/15 text-white text-xs font-semibold cursor-pointer"
          >
            Close Matrix
          </button>
        </div>

      </div>
    </div>
  )

  return createPortal(modalJSX, document.body)
}
