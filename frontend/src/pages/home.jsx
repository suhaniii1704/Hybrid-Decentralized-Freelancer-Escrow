import { ArrowRight, ShieldCheck, Wallet, LockKeyhole } from "lucide-react";
import { Link } from "react-router-dom";

function Home() {
    return (
        <div className="home">

            <section className="hero">

                <div className="hero-content">

                    <div className="badge">
                        <ShieldCheck size={16} />
                        Decentralized & Secure
                    </div>

                    <h1>
                        Work with trust.
                        <br />
                        <span>Get paid securely.</span>
                    </h1>

                    <p>
                        A decentralized freelancer escrow platform that
                        protects both clients and freelancers using
                        blockchain-powered smart contracts.
                    </p>

                    <div className="hero-buttons">
                    <Link to="/signup" className="primary-btn">
                        Get Started
                     <ArrowRight size={18} />
             </Link>

                        <button className="secondary-btn">
                            How It Works
                        </button>
                    </div>

                    <div className="stats">
                        <div>
                            <strong>100%</strong>
                            <small>Secure Escrow</small>
                        </div>

                        <div>
                            <strong>Web3</strong>
                            <small>Powered</small>
                        </div>

                        <div>
                            <strong>24/7</strong>
                            <small>Transparent</small>
                        </div>
                    </div>

                </div>

                <div className="hero-card">

                    <div className="floating-card card-one">
                        <Wallet size={20} />
                        <div>
                            <strong>Escrow Funded</strong>
                            <small>Payment secured</small>
                        </div>
                    </div>

                    <div className="contract-card">
                        <div className="contract-icon">
                            <LockKeyhole size={32} />
                        </div>

                        <h3>Smart Contract</h3>

                        <p>
                            Funds are locked securely until
                            project milestones are completed.
                        </p>

                        <div className="contract-status">
                            <span></span>
                            Contract Active
                        </div>
                    </div>

                </div>

            </section>

            <section className="features" id="features">

                <h2>Everything you need for secure freelancing</h2>

                <div className="feature-grid">

                    <div className="feature-card">
                        <ShieldCheck />
                        <h3>Secure Escrow</h3>
                        <p>
                            Payments are protected by blockchain
                            smart contracts.
                        </p>
                    </div>

                    <div className="feature-card">
                        <LockKeyhole />
                        <h3>Milestone Payments</h3>
                        <p>
                            Release funds only when agreed work
                            is completed.
                        </p>
                    </div>

                    <div className="feature-card">
                        <Wallet />
                        <h3>Web3 Payments</h3>
                        <p>
                            Connect your wallet and interact
                            directly with the escrow contract.
                        </p>
                    </div>

                </div>

            </section>

        </div>
    );
}

export default Home;