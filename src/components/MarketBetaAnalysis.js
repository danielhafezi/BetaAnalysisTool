import { useState, useEffect } from 'react';
import { useRecoilState } from 'recoil';
import { marketBetaResultsState } from '../atoms/marketBetaState';

function MarketBetaAnalysis() {
    const [results, setResults] = useRecoilState(marketBetaResultsState);
    const [loading, setLoading] = useState(false);
    const [timeRange, setTimeRange] = useState('24h');
    
    const handleAnalysis = async () => {
        setLoading(true);
        try {
            const response = await fetch('/api/market-beta', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ timeRange }),
            });
            const data = await response.json();
            console.log('Received data from API:', data);
            setResults(data);
        } catch (error) {
            console.error('Error:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        console.log('Results updated:', results);
    }, [results]);

    const handleDownloadCSV = async () => {
        try {
            const response = await fetch('/api/download-csv', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ results }),
            });
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'market_beta_analysis.csv';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            a.remove();
        } catch (error) {
            console.error('Error downloading CSV:', error);
        }
    };

    return (
        <div className="p-4">
            <div className="mb-4">
                <select 
                    value={timeRange} 
                    onChange={(e) => setTimeRange(e.target.value)}
                    className="mr-2 p-2 border rounded"
                >
                    <option value="24h">Last 24 Hours</option>
                    <option value="7d">Last 7 Days</option>
                    <option value="30d">Last 30 Days</option>
                </select>
                <button 
                    onClick={handleAnalysis}
                    className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
                    disabled={loading}
                >
                    {loading ? 'Analyzing...' : 'Analyze Beta Patterns'}
                </button>
                <button 
                    onClick={handleDownloadCSV} 
                    disabled={!results || Object.keys(results).length === 0}
                    className="ml-2 px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
                >
                    Download CSV
                </button>
            </div>

            {loading && <div className="text-center">Loading...</div>}

            {results?.current_window && (
                <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg shadow">
                    <h3 className="text-lg font-semibold mb-2 text-blue-800">Current Time Window Beta</h3>
                    <div className="text-gray-700">
                        <div className="flex items-center space-x-2">
                            <span className="font-medium">{results.current_window.day}</span>
                            <span>at</span>
                            <span className="font-medium">{results.current_window.time}</span>
                        </div>
                        {results.current_window.beta !== null ? (
                            <div className="mt-2">
                                <span className="text-xl font-bold text-blue-600">
                                    Beta: {results.current_window.beta}
                                </span>
                                <span className="ml-2 text-sm text-gray-600">
                                    (based on {results.current_window.samples} samples)
                                </span>
                            </div>
                        ) : (
                            <div className="mt-2 text-yellow-600">
                                Insufficient data for current time window
                            </div>
                        )}
                    </div>
                </div>
            )}

            {results && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Highest Beta Table */}
                    <div className="bg-white rounded-lg shadow overflow-hidden">
                        <h3 className="text-lg font-semibold p-4 bg-gray-50">Highest Beta Time Windows</h3>
                        <div className="overflow-x-auto">
                            <table className="min-w-full">
                                <thead className="bg-gray-50">
                                    <tr>
                                        <th className="px-4 py-2 text-left">Rank</th>
                                        <th className="px-4 py-2 text-left">Day</th>
                                        <th className="px-4 py-2 text-left">Time</th>
                                        <th className="px-4 py-2 text-left">Beta</th>
                                        <th className="px-4 py-2 text-left">Samples</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {results.highest_beta?.map((item) => (
                                        <tr key={`${item.day}-${item.time}-${item.rank}`} className="border-t">
                                            <td className="px-4 py-2">{item.rank}</td>
                                            <td className="px-4 py-2">{item.day}</td>
                                            <td className="px-4 py-2">{item.time}</td>
                                            <td className="px-4 py-2">{item.beta}</td>
                                            <td className="px-4 py-2">{item.samples}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>

                    {/* Lowest Beta Table */}
                    <div className="bg-white rounded-lg shadow overflow-hidden">
                        <h3 className="text-lg font-semibold p-4 bg-gray-50">Lowest Beta Time Windows</h3>
                        <div className="overflow-x-auto">
                            <table className="min-w-full">
                                <thead className="bg-gray-50">
                                    <tr>
                                        <th className="px-4 py-2 text-left">Rank</th>
                                        <th className="px-4 py-2 text-left">Day</th>
                                        <th className="px-4 py-2 text-left">Time</th>
                                        <th className="px-4 py-2 text-left">Beta</th>
                                        <th className="px-4 py-2 text-left">Samples</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {results.lowest_beta?.map((item) => (
                                        <tr key={`${item.day}-${item.time}-${item.rank}`} className="border-t">
                                            <td className="px-4 py-2">{item.rank}</td>
                                            <td className="px-4 py-2">{item.day}</td>
                                            <td className="px-4 py-2">{item.time}</td>
                                            <td className="px-4 py-2">{item.beta}</td>
                                            <td className="px-4 py-2">{item.samples}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

export default MarketBetaAnalysis; 