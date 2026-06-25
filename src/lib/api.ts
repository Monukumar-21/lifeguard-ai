import { Task } from "./types";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export interface PriorityTask {
  id: string;
  title: string;
  due: string;
  urgency: "high" | "medium" | "low";
}

export interface DeadlineData {
  day: string;
  tasks: number;
}

export interface GoalData {
  id: string;
  title: string;
  progress: number;
  total: number;
  completed: number;
}

export interface SubscriptionData {
  id: string;
  name: string;
  amount: string;
  renewsIn: number;
}

export async function getTodaysPriorities(userId: string): Promise<PriorityTask[]> {
  try {
    const res = await fetch(`${API_URL}/tasks/?user_id=${userId}`);
    if (!res.ok) throw new Error("Failed to fetch");
    const tasks = await res.json();
    return tasks
      .filter((t: any) => t.status === "PENDING")
      .sort((a: any, b: any) => b.priority - a.priority)
      .slice(0, 3)
      .map((t: any) => ({
        id: t.id,
        title: t.title,
        due: t.due_date ? new Date(t.due_date).toLocaleString() : "No due date",
        urgency: t.priority >= 4 ? "high" : t.priority >= 3 ? "medium" : "low"
      }));
  } catch (err) {
    return [
      { id: "1", title: "Finalize Series A Pitch Deck", due: "Today, 5:00 PM", urgency: "high" },
      { id: "2", title: "Review Q3 Marketing Budget", due: "Tomorrow, 10:00 AM", urgency: "medium" },
      { id: "3", title: "Approve New Hires", due: "Tomorrow, 2:00 PM", urgency: "low" }
    ];
  }
}

export async function getUpcomingDeadlines(userId: string): Promise<DeadlineData[]> {
  try {
    const res = await fetch(`${API_URL}/tasks/?user_id=${userId}`);
    if (!res.ok) throw new Error("Failed to fetch");
    const tasks = await res.json();
    
    const deadlines = Array(7).fill(0).map((_, i) => {
      const d = new Date();
      d.setDate(d.getDate() + i);
      return {
        day: d.toLocaleDateString("en-US", { weekday: "short" }),
        tasks: 0,
        date: d.toDateString()
      };
    });

    tasks.forEach((task: any) => {
      if (task.due_date && task.status === "PENDING") {
        const taskDate = new Date(task.due_date).toDateString();
        const dayIndex = deadlines.findIndex(d => d.date === taskDate);
        if (dayIndex !== -1) {
          deadlines[dayIndex].tasks++;
        }
      }
    });

    return deadlines.map(d => ({ day: d.day, tasks: d.tasks }));
  } catch (err) {
    // Return mock data for preview
    return [
      { day: "Mon", tasks: 2 },
      { day: "Tue", tasks: 4 },
      { day: "Wed", tasks: 1 },
      { day: "Thu", tasks: 3 },
      { day: "Fri", tasks: 5 },
      { day: "Sat", tasks: 0 },
      { day: "Sun", tasks: 1 },
    ];
  }
}

export async function getGoals(userId: string): Promise<GoalData[]> {
  try {
    const res = await fetch(`${API_URL}/goals/?user_id=${userId}`);
    if (!res.ok) throw new Error("Failed to fetch");
    const goals = await res.json();
    
    return goals.map((g: any) => ({
      id: g.id,
      title: g.title,
      progress: 0, // Backend needs to provide this
      total: 10,
      completed: 0
    }));
  } catch (err) {
    return [
      { id: "g1", title: "Run 50km this month", progress: 60, total: 50, completed: 30 },
      { id: "g2", title: "Read 3 books", progress: 33, total: 3, completed: 1 }
    ];
  }
}

export async function getSubscriptions(userId: string): Promise<SubscriptionData[]> {
  try {
    const res = await fetch(`${API_URL}/subscriptions/status?user_id=${userId}`);
    if (!res.ok) throw new Error("Failed to fetch");
    const sub = await res.json();
    
    if (sub.status === "inactive") return [];
    
    return [{
      id: sub.plan,
      name: sub.plan === "none" ? "Free Plan" : sub.plan,
      amount: "$0",
      renewsIn: 30
    }];
  } catch (err) {
    return [{
      id: "pro",
      name: "LifeGuard Pro",
      amount: "$15.00",
      renewsIn: 12
    }];
  }
}
