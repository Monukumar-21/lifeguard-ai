export interface Task {
  id: string;
  title: string;
  description?: string;
  due_date?: string;
  status: "PENDING" | "IN_PROGRESS" | "COMPLETED" | "FAILED" | "CANCELLED";
  priority: number;
}
