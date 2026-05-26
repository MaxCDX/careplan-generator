type CarePlanResultProps = {
  carePlanContent: string
}

export function CarePlanResult({ carePlanContent }: CarePlanResultProps) {
  if (!carePlanContent) {
    return null
  }

  return (
    <section style={{ marginTop: 24 }}>
      <h2>Generated Care Plan</h2>
      <pre style={{ whiteSpace: 'pre-wrap', border: '1px solid #ddd', padding: 16 }}>
        {carePlanContent}
      </pre>
    </section>
  )
}
