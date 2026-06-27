import React, { useEffect, useState } from "react";
import { motion } from "motion/react";
import { 
  Activity, 
  LayoutDashboard, 
  Target, 
  ListTodo, 
  CreditCard,
  MessageCircle,
  Clock,
  AlertTriangle,
  CheckCircle2,
  AlertCircle
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "./components/ui/card";
import { Badge } from "./components/ui/badge";
import { Progress } from "./components/ui/progress";
import { Button } from "./components/ui/button";
import { Skeleton } from "./components/ui/skeleton";
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  Cell
} from "recharts";
import {
  getTodaysPriorities,
  getUpcomingDeadlines,
  getGoals,
  getSubscriptions,
  PriorityTask,
  DeadlineData,
  GoalData,
  SubscriptionData
} from "./lib/api";

const user = { name: "Alex" };
const MOCK_USER_ID = "00000000-0000-0000-0000-000000000000";

const recentMessages = [
  { id: 1, from: "bot", text: "Got it. I've noted down: Finalize Series A Pitch Deck. I will keep you accountable.", time: "10 mins ago" },
  { id: 2, from: "user", text: "I need to finish the pitch deck by 5pm today", time: "11 mins ago" },
  { id: 3, from: "bot", text: "Good morning! You have 3 tasks due today. What's your first move?", time: "2 hours ago" }
];

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-slate-900 text-white p-3 rounded-xl shadow-lg border border-slate-800 text-sm">
        <p className="font-semibold mb-1 text-slate-100">{label}</p>
        <p className="text-slate-400 text-xs">
          <span className="font-bold text-white text-base">{payload[0].value}</span> tasks due
        </p>
      </div>
    );
  }
  return null;
};

export default function App() {
  const [isSignedIn, setIsSignedIn] = useState(false);
  const [hasProvidedNumber, setHasProvidedNumber] = useState(false);
  const [phoneInput, setPhoneInput] = useState("");
  const [passwordInput, setPasswordInput] = useState("");

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [priorities, setPriorities] = useState<PriorityTask[]>([]);
  const [deadlinesData, setDeadlinesData] = useState<DeadlineData[]>([]);
  const [goals, setGoals] = useState<GoalData[]>([]);
  const [subscriptions, setSubscriptions] = useState<SubscriptionData[]>([]);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError(null);
        
        const [p, d, g, s] = await Promise.all([
          getTodaysPriorities(MOCK_USER_ID),
          getUpcomingDeadlines(MOCK_USER_ID),
          getGoals(MOCK_USER_ID),
          getSubscriptions(MOCK_USER_ID)
        ]);

        setPriorities(p);
        setDeadlinesData(d);
        setGoals(g);
        setSubscriptions(s);
      } catch (err) {
        setError("Failed to load dashboard data. Please try again later.");
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [isSignedIn, hasProvidedNumber]);

  if (!isSignedIn) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center font-sans">
        <Card className="w-[400px] shadow-sm border-slate-200">
          <CardHeader className="text-center">
            <Activity className="w-12 h-12 mx-auto text-slate-900 mb-2" />
            <CardTitle className="text-2xl font-bold">LifeGuard AI</CardTitle>
            <CardDescription>Your personal AI accountability partner.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Button onClick={() => setIsSignedIn(true)} className="w-full bg-slate-900 text-white hover:bg-slate-800">
              Sign In to Dashboard
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!hasProvidedNumber) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center font-sans">
        <Card className="w-[400px] shadow-sm border-slate-200">
          <CardHeader className="text-center">
            <MessageCircle className="w-12 h-12 mx-auto text-slate-900 mb-2" />
            <CardTitle className="text-xl font-bold">Connect WhatsApp</CardTitle>
            <CardDescription>Enter your WhatsApp number to start receiving AI coaching and reminders. No need to visit the app again!</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-3">
              <input 
                type="text" 
                placeholder="+91 98765 43210" 
                value={phoneInput}
                onChange={(e) => setPhoneInput(e.target.value)}
                className="flex h-10 w-full rounded-md border border-slate-300 bg-transparent px-3 py-2 text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-900"
              />
              <input 
                type="password" 
                placeholder="Create a 4-digit PIN (e.g. 1234)" 
                value={passwordInput}
                onChange={(e) => setPasswordInput(e.target.value)}
                className="flex h-10 w-full rounded-md border border-slate-300 bg-transparent px-3 py-2 text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-900"
              />
            </div>
            <Button 
              onClick={async () => {
                if (!phoneInput || !passwordInput) {
                  alert("Please provide both phone number and a PIN.");
                  return;
                }
                const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
                try {
                  setLoading(true);
                  await fetch(`${API_URL}/whatsapp/connect`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ whatsapp_number: phoneInput, password: passwordInput })
                  });
                } catch (e) {
                  console.error("Failed to connect whatsapp", e);
                } finally {
                  setLoading(false);
                  setHasProvidedNumber(true);
                }
              }} 
              className="w-full bg-slate-900 text-white hover:bg-slate-800"
              disabled={loading}
            >
              {loading ? "Connecting..." : "Connect & Start"}
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 flex text-slate-900 font-sans">
      {/* Sidebar Navigation */}
      <aside className="w-64 bg-slate-50 border-r border-slate-200 flex-col hidden md:flex">
        <div className="p-6">
          <div className="flex items-center gap-2 font-bold text-xl text-slate-900 mb-8 tracking-tight">
            <Activity className="text-black w-6 h-6" />
            <span>LifeGuard AI</span>
          </div>
          <nav className="space-y-1">
            <a href="#" className="flex items-center gap-3 px-3 py-2 bg-slate-100 text-slate-900 rounded-lg font-medium text-sm">
              <LayoutDashboard className="w-4 h-4" /> Dashboard
            </a>
            <a href="#" className="flex items-center gap-3 px-3 py-2 text-slate-500 hover:text-slate-900 hover:bg-slate-100 rounded-lg font-medium text-sm transition-colors">
              <ListTodo className="w-4 h-4" /> Tasks
            </a>
            <a href="#" className="flex items-center gap-3 px-3 py-2 text-slate-500 hover:text-slate-900 hover:bg-slate-100 rounded-lg font-medium text-sm transition-colors">
              <Target className="w-4 h-4" /> Goals
            </a>
            <a href="#" className="flex items-center gap-3 px-3 py-2 text-slate-500 hover:text-slate-900 hover:bg-slate-100 rounded-lg font-medium text-sm transition-colors">
              <CreditCard className="w-4 h-4" /> Billing
            </a>
          </nav>
        </div>
        <div className="mt-auto p-6 space-y-3">
          <div className="bg-amber-50 border border-amber-100 p-3 rounded-xl text-center">
            <p className="text-[11px] font-semibold text-amber-700 uppercase tracking-wider">Free Plan</p>
            <p className="text-[10px] text-amber-600 mt-0.5">10 messages / day</p>
          </div>
          <div className="bg-slate-50 border border-slate-100 p-4 rounded-xl">
            <h4 className="text-sm font-semibold text-slate-900 mb-1">Upgrade to Premium</h4>
            <p className="text-xs text-slate-500 mb-3">Unlimited AI messages for ₹50.</p>
            <Button onClick={() => alert("\u2728 Premium feature is in progress!\n\nThis will unlock:\n\u2022 Unlimited WhatsApp messages\n\u2022 Priority AI responses\n\u2022 Advanced analytics\n\nComing soon!")} variant="outline" size="sm" className="w-full text-xs font-medium bg-slate-900 text-white hover:bg-slate-800 hover:text-white border-0">Upgrade Now</Button>
          </div>
          <Button onClick={() => { setIsSignedIn(false); setHasProvidedNumber(false); }} variant="ghost" size="sm" className="w-full text-xs text-slate-400 hover:text-slate-900">Sign Out</Button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 p-8 md:p-12 overflow-y-auto h-screen">
        <motion.header 
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-10 flex justify-between items-end"
        >
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-slate-900">
              Good morning, {user.name}.
            </h1>
            <div className="text-slate-500 mt-1 text-sm">
              {loading ? (
                <Skeleton className="h-5 w-64" />
              ) : error ? (
                <span className="text-red-500 flex items-center gap-2"><AlertCircle className="w-4 h-4" /> Error loading data</span>
              ) : (
                `You have ${priorities.length} critical priorities today.`
              )}
            </div>
          </div>
          <Button className="bg-slate-900 hover:bg-slate-800 text-white font-medium rounded-full px-6 shadow-sm">
            + New Commitment
          </Button>
        </motion.header>

        {/* Productivity Trend */}
        <motion.section 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mb-8"
        >
            <h2 className="text-sm font-semibold mb-4 text-slate-900 uppercase tracking-wider">Productivity Trend</h2>
            <div className="h-32 w-full bg-white border border-slate-100 shadow-sm rounded-2xl flex items-end p-4 gap-2">
              {[40, 60, 45, 80, 50, 90, 70, 85, 100, 65, 80, 55, 75, 95].map((val, i) => (
                <div key={i} className="flex-1 h-full flex items-end group relative cursor-crosshair">
                  <motion.div 
                    initial={{ height: 0 }}
                    animate={{ height: `${val}%` }}
                    transition={{ delay: 0.2 + i * 0.02, duration: 0.5, ease: "easeOut" }}
                    className="w-full bg-slate-100 group-hover:bg-slate-900 transition-colors rounded-sm" 
                  />
                  {/* Tooltip */}
                  <div className="opacity-0 group-hover:opacity-100 transition-opacity duration-200 absolute -top-10 left-1/2 -translate-x-1/2 bg-slate-900 text-white text-xs py-1.5 px-2.5 rounded-lg shadow-xl pointer-events-none whitespace-nowrap z-10 font-medium">
                    Score: {val}
                    <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-900" />
                  </div>
                </div>
              ))}
            </div>
        </motion.section>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-10">
          
          {/* Left Column (Wider) */}
          <div className="lg:col-span-2 space-y-10">
            
            {/* Top Priorities */}
            <motion.section
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-semibold text-slate-900 uppercase tracking-wider">
                  Top Priorities
                </h2>
                <a href="#" className="text-xs font-semibold text-slate-500 hover:text-slate-900">View all</a>
              </div>
              
              <div className="grid gap-3">
                {loading ? (
                  [1, 2, 3].map(i => <Skeleton key={i} className="h-20 w-full rounded-2xl" />)
                ) : priorities.length > 0 ? (
                  priorities.map((task, i) => (
                    <motion.div 
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.3 + i * 0.05 }}
                      whileHover={{ scale: 1.01 }}
                      key={task.id} 
                      className="flex items-center justify-between p-4 bg-white rounded-2xl border border-slate-100 shadow-sm cursor-pointer"
                    >
                        <div className="flex items-center gap-4">
                          <button className="h-5 w-5 rounded-full border border-slate-300 hover:border-slate-900 transition-colors flex items-center justify-center group">
                            <CheckCircle2 className="w-3 h-3 text-transparent group-hover:text-slate-900 transition-colors" />
                          </button>
                          <div>
                            <p className="font-medium text-sm text-slate-900">{task.title}</p>
                            <div className="flex items-center gap-1 text-xs text-slate-500 mt-0.5">
                              <span>{task.due}</span>
                            </div>
                          </div>
                        </div>
                        <Badge variant="outline" className={`text-[10px] font-medium border-0 uppercase ${
                          task.urgency === 'high' ? 'bg-red-50 text-red-600' : 
                          task.urgency === 'medium' ? 'bg-amber-50 text-amber-600' : 'bg-green-50 text-green-600'
                        }`}>
                          {task.urgency}
                        </Badge>
                    </motion.div>
                  ))
                ) : (
                  <div className="p-6 text-center text-sm text-slate-500 bg-white rounded-2xl border border-dashed border-slate-200">
                    No pending priorities. Take a break!
                  </div>
                )}
              </div>
            </motion.section>

            {/* Weekly Deadlines Timeline */}
            <motion.section
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
            >
              <h2 className="text-sm font-semibold text-slate-900 uppercase tracking-wider mb-4">
                  Upcoming Deadlines
              </h2>
              <div className="h-64 bg-white border border-slate-100 shadow-sm rounded-2xl p-6">
                  {loading ? (
                    <Skeleton className="w-full h-full" />
                  ) : (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={deadlinesData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }} barSize={32}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                        <XAxis 
                          dataKey="day" 
                          axisLine={false} 
                          tickLine={false} 
                          tick={{ fill: '#94a3b8', fontSize: 12 }} 
                          dy={10}
                        />
                        <YAxis 
                          axisLine={false} 
                          tickLine={false} 
                          tick={{ fill: '#94a3b8', fontSize: 12 }}
                          allowDecimals={false}
                        />
                        <Tooltip 
                          cursor={{ fill: '#f8fafc', radius: [6, 6, 0, 0] }}
                          content={<CustomTooltip />}
                        />
                        <Bar dataKey="tasks" radius={[6, 6, 0, 0]}>
                          {
                            deadlinesData.map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={entry.tasks > 2 ? '#0f172a' : '#cbd5e1'} />
                            ))
                          }
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  )}
              </div>
            </motion.section>
          </div>

          {/* Right Column (Narrow) */}
          <div className="space-y-10">
            
            {/* Active Goals (using clean progress) */}
            <motion.section
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
            >
              <h2 className="text-sm font-semibold text-slate-900 uppercase tracking-wider mb-4">Active Goals</h2>
              <div className="space-y-3">
                {loading ? (
                  [1, 2].map(i => <Skeleton key={i} className="h-24 w-full rounded-2xl" />)
                ) : goals.length > 0 ? (
                  goals.map((goal, i) => (
                    <motion.div 
                      initial={{ opacity: 0, x: 10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.5 + i * 0.1 }}
                      whileHover={{ scale: 1.02 }}
                      key={goal.id} 
                      className="p-5 bg-white border border-slate-100 shadow-sm rounded-2xl"
                    >
                        <div className="flex justify-between items-end mb-3">
                          <div>
                            <h4 className="font-medium text-sm text-slate-900">{goal.title}</h4>
                            <p className="text-[11px] font-medium text-slate-500 mt-0.5 uppercase tracking-wide">{goal.completed} of {goal.total} tasks</p>
                          </div>
                          <span className="text-xs font-bold text-slate-900">{goal.progress}%</span>
                        </div>
                        <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
                           <div className="h-full bg-slate-900 rounded-full" style={{ width: `${goal.progress}%` }} />
                        </div>
                    </motion.div>
                  ))
                ) : (
                  <div className="p-8 flex flex-col items-center justify-center text-center text-slate-500 bg-white border border-slate-200 shadow-sm rounded-2xl border-dashed">
                    <Target className="w-8 h-8 text-slate-300 mb-3" strokeWidth={1.5} />
                    <p className="text-sm font-medium text-slate-900 mb-1">No active goals</p>
                    <p className="text-xs text-slate-500">You're all caught up for now.</p>
                  </div>
                )}
              </div>
            </motion.section>

            {/* Upcoming Renewals */}
            <motion.section
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 }}
            >
              <h2 className="text-sm font-semibold text-slate-900 uppercase tracking-wider mb-4">Upcoming Renewals</h2>
              <div className="bg-white border border-slate-100 shadow-sm rounded-2xl divide-y divide-slate-100">
                  {loading ? (
                    <div className="p-4"><Skeleton className="h-10 w-full" /></div>
                  ) : subscriptions.map(sub => (
                    <div key={sub.id} className="p-4 flex items-center justify-between hover:bg-slate-50 transition-colors">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-slate-900">
                          <CreditCard className="w-3 h-3" />
                        </div>
                        <div>
                          <p className="font-medium text-sm text-slate-900">{sub.name}</p>
                          <p className="text-[11px] text-slate-500">Renews in {sub.renewsIn} days</p>
                        </div>
                      </div>
                      <span className="font-semibold text-sm text-slate-900">{sub.amount}</span>
                    </div>
                  ))}
                  {!loading && subscriptions.length === 0 && (
                    <div className="p-8 flex flex-col items-center justify-center text-center text-slate-500 bg-white">
                      <CreditCard className="w-8 h-8 text-slate-300 mb-3" strokeWidth={1.5} />
                      <p className="text-sm font-medium text-slate-900 mb-1">No upcoming renewals</p>
                      <p className="text-xs text-slate-500">No bills due in the next 30 days.</p>
                    </div>
                  )}
              </div>
            </motion.section>

            {/* WhatsApp Feed */}
            <motion.section
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6 }}
            >
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-semibold text-slate-900 uppercase tracking-wider">Agent Feed</h2>
                <MessageCircle className="w-4 h-4 text-slate-400" />
              </div>
              <div className="bg-white border border-slate-100 shadow-sm rounded-2xl p-4 space-y-4">
                  {recentMessages.map((msg, i) => (
                    <motion.div 
                      initial={{ opacity: 0, scale: 0.95 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: 0.7 + i * 0.1 }}
                      key={msg.id} 
                      className={`flex flex-col ${msg.from === 'user' ? 'items-end' : 'items-start'}`}
                    >
                      <div className={`
                        max-w-[85%] px-4 py-2 text-sm
                        ${msg.from === 'user' 
                          ? 'bg-slate-900 text-white rounded-2xl rounded-br-sm' 
                          : 'bg-white border border-slate-200 text-slate-900 rounded-2xl rounded-bl-sm'}
                      `}>
                        {msg.text}
                      </div>
                      <span className="text-[10px] font-medium text-slate-400 mt-1 px-1 uppercase">{msg.time}</span>
                    </motion.div>
                  ))}
              </div>
            </motion.section>

          </div>
        </div>
      </main>
    </div>
  );
}
