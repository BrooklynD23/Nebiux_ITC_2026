import type { DashboardUser } from '../data/admin';

interface UserTableProps {
  readonly users: readonly DashboardUser[];
}

export function UserTable({ users }: UserTableProps): JSX.Element {
  return (
    <div className="user-table-wrapper">
      <table className="user-table">
        <thead>
          <tr>
            <th>User</th>
            <th>Role</th>
            <th>Status</th>
            <th>Conversations</th>
            <th>Last question</th>
            <th>Channel</th>
            <th>Satisfaction</th>
          </tr>
        </thead>
        <tbody>
          {users.map((user) => (
            <tr key={user.id}>
              <td>{user.name}</td>
              <td>{user.role}</td>
              <td>{user.status}</td>
              <td>{user.conversations}</td>
              <td>{user.lastQuestion}</td>
              <td>{user.channel}</td>
              <td>{user.satisfaction}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
