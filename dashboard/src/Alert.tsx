export function Alert({ message }: Readonly<{ message: string | null }>) {
  if (!message) return null;
  return (
    <p className="alert" role="alert">
      {message}
    </p>
  );
}
