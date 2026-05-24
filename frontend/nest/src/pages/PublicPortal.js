import React, { useState, useEffect } from 'react';
import { HiOutlineBookOpen, HiOutlineQuestionMarkCircle, HiOutlineChat, HiOutlineSearch, HiOutlineChevronDown, HiOutlineChevronUp } from 'react-icons/hi';
import { getApiBase } from '../context/AuthContext';

const BEST_PRACTICES = [
  {
    id: 'social-enterprise-basics',
    category: 'Getting Started',
    title: 'What is a Social Enterprise?',
    summary: 'Learn about social enterprises and how they create both social impact and sustainable revenue.',
    content: `A social enterprise is a business that prioritizes social, environmental, or community objectives alongside financial sustainability. Unlike traditional nonprofits, social enterprises generate revenue through commercial activities while reinvesting profits to further their mission.

Key characteristics:
• Mission-driven: Primary goal is to address social or environmental challenges
• Revenue-generating: Operates as a business with products or services
• Impact-focused: Measures success by social outcomes, not just profits
• Sustainable: Aims for financial self-sufficiency

Knowledge Navigator supports social enterprises that create employment and income opportunities for people living in poverty.`,
  },
  {
    id: 'kn-support',
    category: 'Getting Started',
    title: 'How Knowledge Navigator Supports Social Enterprises',
    summary: 'Discover the comprehensive support Knowledge Navigator provides to help social enterprises grow and scale.',
    content: `Knowledge Navigator provides a unique combination of patient capital and tailored capacity development to help social enterprises achieve sustainable growth.

Our support includes:
• Investment Capital: Flexible financing adapted to enterprise needs
• Business Development: Strategic planning and operational support
• Market Access: Connections to new customers and markets
• Mentorship: Access to experienced business advisors
• Network: Connection to a community of social entrepreneurs

We work with enterprises from early stage through growth, typically over 5-7 years.`,
  },
  {
    id: 'impact-measurement',
    category: 'Impact',
    title: 'Measuring Social Impact',
    summary: 'Understanding how to measure and report the social impact of your enterprise.',
    content: `Measuring social impact is essential for understanding your enterprise's effectiveness and communicating value to stakeholders.

Key impact metrics to track:
• Jobs created or sustained
• Income generated for beneficiaries
• Number of people reached
• Environmental outcomes (if applicable)
• Quality of life improvements

Best practices:
1. Define clear impact goals aligned with your mission
2. Establish baseline measurements before interventions
3. Collect data regularly and consistently
4. Use both quantitative and qualitative measures
5. Report transparently to stakeholders`,
  },
  {
    id: 'financial-sustainability',
    category: 'Business Development',
    title: 'Building Financial Sustainability',
    summary: 'Strategies for achieving long-term financial health while maintaining social mission.',
    content: `Financial sustainability ensures your social enterprise can continue creating impact over the long term.

Key strategies:
• Diversify revenue streams: Don't rely on a single product or customer
• Understand your unit economics: Know your costs and margins
• Build cash reserves: Maintain 3-6 months of operating expenses
• Plan for growth: Invest in capacity before you need it
• Balance mission and margin: Ensure pricing supports both impact and sustainability

Common pitfalls to avoid:
• Underpricing products/services
• Over-reliance on grants or donations
• Scaling too quickly without infrastructure
• Neglecting financial management systems`,
  },
  {
    id: 'scaling-strategies',
    category: 'Business Development',
    title: 'Scaling Your Social Enterprise',
    summary: 'Proven approaches for growing your impact while maintaining quality and mission.',
    content: `Scaling a social enterprise requires careful planning to grow impact without compromising quality or mission.

Scaling approaches:
• Organic growth: Gradually expand existing operations
• Replication: Open new locations or branches
• Franchising: License your model to others
• Partnerships: Collaborate with larger organizations
• Technology: Use digital tools to reach more people

Before scaling, ensure you have:
1. A proven, replicable model
2. Strong operational systems
3. Adequate financing
4. The right team
5. Clear impact metrics`,
  },
  {
    id: 'market-access',
    category: 'Market Development',
    title: 'Accessing New Markets',
    summary: 'How to identify and enter new markets for your products or services.',
    content: `Expanding into new markets can significantly increase your enterprise's impact and revenue.

Market entry strategies:
• Research: Understand customer needs and competition
• Partnerships: Work with established players in new markets
• Digital channels: Use e-commerce and social media
• B2B sales: Sell to businesses, institutions, or government
• Export: Explore international opportunities

Tips for success:
1. Start with markets similar to your current ones
2. Test with small pilots before full commitment
3. Adapt products/services to local needs
4. Build relationships before transactions
5. Be patient - market development takes time`,
  },
];

const FAQS = [
  {
    id: 'faq-1',
    question: 'What types of social enterprises does Knowledge Navigator support?',
    answer: 'Knowledge Navigator supports social enterprises that create dignified employment and income opportunities for people living in poverty. We focus on enterprises in sectors like sustainable agriculture, artisan production, recycling, and services that employ or benefit marginalized communities.',
  },
  {
    id: 'faq-2',
    question: 'How can I apply for Knowledge Navigator support?',
    answer: 'Social enterprises can apply through our website during open application periods. We look for enterprises with a clear social mission, a viable business model, potential for growth, and commitment to measuring impact. Visit our main website for current opportunities.',
  },
  {
    id: 'faq-3',
    question: 'What kind of investment does Knowledge Navigator provide?',
    answer: 'Knowledge Navigator provides patient capital in the form of loans, equity, and quasi-equity investments. Our investments are tailored to each enterprise\'s needs and stage of development, typically ranging from $50,000 to $500,000 over multiple rounds.',
  },
  {
    id: 'faq-4',
    question: 'How long does Knowledge Navigator work with portfolio enterprises?',
    answer: 'Knowledge Navigator typically works with enterprises for 5-7 years, providing ongoing support as they grow. This long-term approach allows us to provide patient capital and sustained capacity building that enterprises need to achieve sustainable growth.',
  },
  {
    id: 'faq-5',
    question: 'What regions does Knowledge Navigator operate in?',
    answer: 'Knowledge Navigator currently operates in Latin America (Brazil, Chile, Colombia, Peru) and Central Europe (Romania, Croatia). We focus on regions where we can build deep local expertise and networks to support social enterprises effectively.',
  },
  {
    id: 'faq-6',
    question: 'How does Knowledge Navigator measure impact?',
    answer: 'Knowledge Navigator tracks both social and financial metrics for all portfolio enterprises. Key impact indicators include jobs created, income generated for beneficiaries, and people reached. We also track enterprise financial health, revenue growth, and sustainability metrics.',
  },
  {
    id: 'faq-7',
    question: 'Can I volunteer or mentor with Knowledge Navigator?',
    answer: 'Yes! Knowledge Navigator welcomes skilled volunteers and mentors who can support our portfolio enterprises. We particularly need expertise in areas like finance, marketing, operations, and technology. Contact us through our main website to learn about opportunities.',
  },
  {
    id: 'faq-8',
    question: 'How can donors or investors support Knowledge Navigator?',
    answer: 'Donors and investors can support Knowledge Navigator through grants to our operating fund, investments in our enterprise fund, or sponsorship of specific programs. We offer various engagement levels and reporting to match donor interests and requirements.',
  },
];

function PublicPortal() {
  const [activeTab, setActiveTab] = useState('library');
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedFaq, setExpandedFaq] = useState(null);
  const [expandedPractice, setExpandedPractice] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [chatQuery, setChatQuery] = useState('');
  const [chatMessages, setChatMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  // Set dark theme for public portal
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', 'dark');
  }, []);

  const categories = ['All', ...new Set(BEST_PRACTICES.map(p => p.category))];

  const filteredPractices = BEST_PRACTICES.filter(practice => {
    const matchesSearch = practice.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      practice.summary.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = selectedCategory === 'All' || practice.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  const filteredFaqs = FAQS.filter(faq =>
    faq.question.toLowerCase().includes(searchQuery.toLowerCase()) ||
    faq.answer.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleAskQuestion = async (e) => {
    e.preventDefault();
    if (!chatQuery.trim() || isLoading) return;

    const userMessage = { role: 'user', content: chatQuery };
    setChatMessages(prev => [...prev, userMessage]);
    setChatQuery('');
    setIsLoading(true);

    try {
      const response = await fetch(`${getApiBase()}/api/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          question: chatQuery,
          session_id: 'public-portal',
          public_mode: true,
        }),
      });

      if (!response.ok) throw new Error('Failed to get response');

      const data = await response.json();
      const assistantMessage = {
        role: 'assistant',
        content: data.answer || 'I apologize, but I could not find relevant information. Please try rephrasing your question or browse our Best Practices Library.',
      };
      setChatMessages(prev => [...prev, assistantMessage]);
    } catch (err) {
      setChatMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again or browse our resources below.',
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="public-portal theme-dark">
      <nav className="public-portal__tabs">
        <button
          type="button"
          className={`public-portal__tab ${activeTab === 'library' ? 'public-portal__tab--active' : ''}`}
          onClick={() => setActiveTab('library')}
        >
          <HiOutlineBookOpen />
          <span>Best Practices Library</span>
        </button>
        <button
          type="button"
          className={`public-portal__tab ${activeTab === 'faq' ? 'public-portal__tab--active' : ''}`}
          onClick={() => setActiveTab('faq')}
        >
          <HiOutlineQuestionMarkCircle />
          <span>FAQ</span>
        </button>
        <button
          type="button"
          className={`public-portal__tab ${activeTab === 'ask' ? 'public-portal__tab--active' : ''}`}
          onClick={() => setActiveTab('ask')}
        >
          <HiOutlineChat />
          <span>Ask a Question</span>
        </button>
      </nav>

      <div className="public-portal__search">
        <HiOutlineSearch className="public-portal__search-icon" />
        <input
          type="text"
          className="public-portal__search-input"
          placeholder={activeTab === 'faq' ? 'Search FAQs...' : 'Search resources...'}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
      </div>

      <main className="public-portal__content">
        {activeTab === 'library' && (
          <div className="public-portal__library">
            <div className="public-portal__categories">
              {categories.map(category => (
                <button
                  key={category}
                  type="button"
                  className={`public-portal__category ${selectedCategory === category ? 'public-portal__category--active' : ''}`}
                  onClick={() => setSelectedCategory(category)}
                >
                  {category}
                </button>
              ))}
            </div>

            <div className="public-portal__practices">
              {filteredPractices.length === 0 ? (
                <p className="public-portal__empty">No resources found matching your search.</p>
              ) : (
                filteredPractices.map(practice => (
                  <article key={practice.id} className="public-portal__practice">
                    <button
                      type="button"
                      className="public-portal__practice-header"
                      onClick={() => setExpandedPractice(expandedPractice === practice.id ? null : practice.id)}
                      aria-expanded={expandedPractice === practice.id}
                    >
                      <div className="public-portal__practice-info">
                        <span className="public-portal__practice-category">{practice.category}</span>
                        <h3 className="public-portal__practice-title">{practice.title}</h3>
                        <p className="public-portal__practice-summary">{practice.summary}</p>
                      </div>
                      {expandedPractice === practice.id ? (
                        <HiOutlineChevronUp className="public-portal__practice-icon" />
                      ) : (
                        <HiOutlineChevronDown className="public-portal__practice-icon" />
                      )}
                    </button>
                    {expandedPractice === practice.id && (
                      <div className="public-portal__practice-content">
                        {practice.content.split('\n\n').map((paragraph, idx) => (
                          <p key={idx}>{paragraph}</p>
                        ))}
                      </div>
                    )}
                  </article>
                ))
              )}
            </div>
          </div>
        )}

        {activeTab === 'faq' && (
          <div className="public-portal__faq">
            {filteredFaqs.length === 0 ? (
              <p className="public-portal__empty">No FAQs found matching your search.</p>
            ) : (
              filteredFaqs.map(faq => (
                <article key={faq.id} className="public-portal__faq-item">
                  <button
                    type="button"
                    className="public-portal__faq-question"
                    onClick={() => setExpandedFaq(expandedFaq === faq.id ? null : faq.id)}
                    aria-expanded={expandedFaq === faq.id}
                  >
                    <span>{faq.question}</span>
                    {expandedFaq === faq.id ? (
                      <HiOutlineChevronUp className="public-portal__faq-icon" />
                    ) : (
                      <HiOutlineChevronDown className="public-portal__faq-icon" />
                    )}
                  </button>
                  {expandedFaq === faq.id && (
                    <div className="public-portal__faq-answer">
                      <p>{faq.answer}</p>
                    </div>
                  )}
                </article>
              ))
            )}
          </div>
        )}

        {activeTab === 'ask' && (
          <div className="public-portal__ask">
            <div className="public-portal__chat-messages">
              {chatMessages.length === 0 ? (
                <div className="public-portal__chat-welcome">
                  <HiOutlineChat className="public-portal__chat-welcome-icon" />
                  <h3>Ask a Question</h3>
                  <p>Have a question about social enterprises or the organization's work? Ask below and we'll help you find the answer.</p>
                  <div className="public-portal__suggested-questions">
                    <p>Try asking:</p>
                    <button type="button" onClick={() => setChatQuery('What is Knowledge Navigator?')}>
                      What is Knowledge Navigator?
                    </button>
                    <button type="button" onClick={() => setChatQuery('How can I apply for support?')}>
                      How can I apply for support?
                    </button>
                    <button type="button" onClick={() => setChatQuery('What regions does Knowledge Navigator operate in?')}>
                      What regions does Knowledge Navigator operate in?
                    </button>
                  </div>
                </div>
              ) : (
                chatMessages.map((msg, idx) => (
                  <div key={idx} className={`public-portal__chat-message public-portal__chat-message--${msg.role}`}>
                    <div className="public-portal__chat-bubble">
                      {msg.content}
                    </div>
                  </div>
                ))
              )}
              {isLoading && (
                <div className="public-portal__chat-message public-portal__chat-message--assistant">
                  <div className="public-portal__chat-bubble public-portal__chat-bubble--loading">
                    <span></span><span></span><span></span>
                  </div>
                </div>
              )}
            </div>
            <form className="public-portal__chat-form" onSubmit={handleAskQuestion}>
              <input
                type="text"
                className="public-portal__chat-input"
                placeholder="Type your question..."
                value={chatQuery}
                onChange={(e) => setChatQuery(e.target.value)}
                disabled={isLoading}
              />
              <button
                type="submit"
                className="public-portal__chat-submit"
                disabled={!chatQuery.trim() || isLoading}
              >
                Ask
              </button>
            </form>
          </div>
        )}
      </main>

      <footer className="public-portal__footer">
        <p>© {new Date().getFullYear()} Knowledge Navigator. Empowering social enterprises to create lasting change.</p>
      </footer>
    </div>
  );
}

export default PublicPortal;
