using UnityEngine;
using UnityEngine.VFX;

public class P_Presser : MonoBehaviour
{
    [Header("Key")]
    [SerializeField] KeyCode legacyKey = KeyCode.P;   // Old Input Manager fallback

    [Header("Ramp")]
    [SerializeField, Min(0.001f)] float rampDuration = 5f; // seconds to reach max
    [SerializeField] int maxSpawnRate = 10000;             // target value (int target; float will lerp to this)

    VisualEffect vfx;
    static readonly int SpawnRateID = Shader.PropertyToID("Spawn rate");

    bool hasInt, hasFloat;
    bool isHeld;
    float pressStart;

    void Awake()
    {
        vfx = GetComponent<VisualEffect>();
        Debug.Log("[Portal] Awake: VisualEffect component found: " + vfx);
        if (!vfx)
        {
            Debug.LogError("[Portal] No VisualEffect component found.");
            enabled = false;
            return;
        }

        hasInt = vfx.HasInt(SpawnRateID);
        hasFloat = vfx.HasFloat(SpawnRateID);

        if (!hasInt && !hasFloat)
        {
            Debug.LogError("[Portal] VFX property 'Spawn rate' not found. " +
                           "Make sure it's on the VFX Graph Blackboard (exact name, case & spaces) and wired into your Spawner's Rate.");
        }

        // Start at 0
        if (hasInt)   vfx.SetInt(SpawnRateID, 0);
        if (hasFloat) vfx.SetFloat(SpawnRateID, 0f);
    }

    void Update()
    {
        // --- Detect input (supports both systems) ---
        bool down = false, up = false, held = false;

#if ENABLE_INPUT_SYSTEM // New Input System present
        var kbd = UnityEngine.InputSystem.Keyboard.current;
        if (kbd != null)
        {
            down = kbd.pKey.wasPressedThisFrame;
            up   = kbd.pKey.wasReleasedThisFrame;
            held = kbd.pKey.isPressed;
            
        }
#endif
        // Legacy fallback (also works if Active Input Handling = Both)
        down |= Input.GetKeyDown(legacyKey);
        up   |= Input.GetKeyUp(legacyKey);
        held |= Input.GetKey(legacyKey);

        // --- State machine ---
        if (down)
        {
            isHeld = true;
            pressStart = Time.time;
            vfx.Reinit(); // optional reset of the graph
            vfx.Play();
            Debug.Log("[Portal] P down → starting ramp.");

        }

        if (isHeld)
        {
            float t = Mathf.Clamp01((Time.time - pressStart) / rampDuration);
            float valueF = Mathf.Lerp(0f, maxSpawnRate, t);

            if (hasInt)   vfx.SetInt(SpawnRateID, Mathf.RoundToInt(valueF));
            if (hasFloat) vfx.SetFloat(SpawnRateID, valueF);
        }

        if (up)
        {
            isHeld = false;
            if (hasInt)   vfx.SetInt(SpawnRateID, 0);
            if (hasFloat) vfx.SetFloat(SpawnRateID, 0f);
            vfx.Stop();
            Debug.Log("[Portal] P up → reset to 0.");
        }
    }
}
