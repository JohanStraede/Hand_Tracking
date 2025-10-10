using UnityEngine;
using UnityEngine.VFX;

public class PortalVFXController : MonoBehaviour
{
    [SerializeField] private VisualEffect vfx;

    // Cache property IDs (safer & faster than raw strings)
    static readonly int SpawnRateID     = Shader.PropertyToID("Spawn rate");
    static readonly int ColorOverLifeID = Shader.PropertyToID("Color over life");
    static readonly int ParticleSizeID  = Shader.PropertyToID("Particle Size");
    static readonly int LifetimeAID     = Shader.PropertyToID("Lifetime A");
    static readonly int LifetimeBID     = Shader.PropertyToID("Lifetime B");
    static readonly int RandomSpeedID   = Shader.PropertyToID("Random speed");
    static readonly int TangentSpeedID  = Shader.PropertyToID("Tangent speed");
    static readonly int PortalRadiusID  = Shader.PropertyToID("Portal radius");

    void Awake()
    {
        if (!vfx) vfx = GetComponent<VisualEffect>();
    }

    // Examples
    public void SetSpawnRate(float value)    => vfx.SetFloat(SpawnRateID, value);
    public void SetParticleSize(float value) => vfx.SetFloat(ParticleSizeID, value);
    public void SetLifetimeA(float value)    => vfx.SetFloat(LifetimeAID, value);
    public void SetLifetimeB(float value)    => vfx.SetFloat(LifetimeBID, value);
    public void SetRandomSpeed(float value)  => vfx.SetFloat(RandomSpeedID, value);
    public void SetTangentSpeed(float value) => vfx.SetFloat(TangentSpeedID, value);
    public void SetPortalRadius(float value) => vfx.SetFloat(PortalRadiusID, value);

    // If "Color over life" is a Gradient in your Graph:
    public void SetColorOverLife(Gradient g) => vfx.SetGradient(ColorOverLifeID, g);

    // If you’re using an event like the "OnPlay" field in the inspector:
    public void Play()  => vfx.Play();
    public void Stop()  => vfx.Stop();
    public void Reinit()=> vfx.Reinit();
}
