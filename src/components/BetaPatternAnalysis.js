import { useState } from 'react';
import { useRecoilValue, useRecoilState } from 'recoil';
import { marketBetaResultsState, betaPatternResultsState } from '../atoms/marketBetaState';

function BetaPatternAnalysis() {
    const marketBetaResults = useRecoilValue(marketBetaResultsState);
    const [selectedSymbol, setSelectedSymbol] = useState('');
    const [betaPatterns, setBetaPatterns] = useRecoilState(betaPatternResultsState);
    const [loading, setLoading] = useState(false);
    
    const fetchBetaPatterns = async () => {
        if (!selectedSymbol) return;
        
        setLoading(true);
        try {
            const response = await fetch('/api/beta-patterns', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    symbol: selectedSymbol,
                    // Default to last 30 days
                    startTime: Math.floor(Date.now() / 1000) - (30 * 24 * 60 * 60),
                    endTime: Math.floor(Date.now() / 1000)
                }),
            });
            const data = await response.json();
            setBetaPatterns(data);
        } catch (error) {
            console.error('Error:', error);
        } finally {
            setLoading(false);
        }
    };

    const renderPatternTable = (patterns, title) => {
        if (!patterns) return null;
        
        return (
            <div className="mt-4">
                <h3 className="text-xl font-bold mb-2">{title}</h3>
                <table className="min-w-full bg-white border border-gray-300">
                    <thead>
                        <tr>
                            <th className="px-4 py-2 border">Day</th>
                            <th className="px-4 py-2 border">Time Window</th>
                            <th className="px-4 py-2 border">Beta</th>
                            <th className="px-4 py-2 border">Samples</th>
                        </tr>
                    </thead>
                    <tbody>
                        {patterns.map((pattern, index) => (
                            <tr key={index} className={index % 2 === 0 ? 'bg-gray-50' : ''}>
                                <td className="px-4 py-2 border">{pattern.day}</td>
                                <td className="px-4 py-2 border">{pattern.time}</td>
                                <td className="px-4 py-2 border">{pattern.beta}</td>
                                <td className="px-4 py-2 border">{pattern.samples}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        );
    };

    return (
        <div className="p-4">
            <div className="mb-4">
                <select
                    value={selectedSymbol}
                    onChange={(e) => setSelectedSymbol(e.target.value)}
                    className="border p-2 rounded"
                >
                    <option value="">Select a symbol</option>
                    {marketBetaResults && Object.keys(marketBetaResults).map(symbol => (
                        <option key={symbol} value={symbol}>{symbol}</option>
                    ))}
                </select>
                <button
                    onClick={fetchBetaPatterns}
                    disabled={!selectedSymbol || loading}
                    className="ml-2 px-4 py-2 bg-blue-500 text-white rounded disabled:bg-gray-300"
                >
                    {loading ? 'Loading...' : 'Analyze Patterns'}
                </button>
            </div>

            {betaPatterns && (
                <div>
                    {renderPatternTable(betaPatterns.highest_beta, 'Highest Beta Time Windows')}
                    {renderPatternTable(betaPatterns.lowest_beta, 'Lowest Beta Time Windows')}
                </div>
            )}
        </div>
    );
}

export default BetaPatternAnalysis; 