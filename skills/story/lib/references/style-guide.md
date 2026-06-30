# Default Style Guide: Watercolor Storybook

## Art Direction

The default illustration style for Story Maker is **watercolor storybook** — warm, soft, and inviting illustrations reminiscent of classic children's picture books.

## Style Prompt Preamble

Include this preamble (adapted for the specific story) in every illustration prompt:

```
A watercolor storybook illustration, children's picture book quality.
Soft brushstrokes with visible texture. Warm, gentle color palette.
[Scene-specific content here].
Aspect ratio 16:9, detailed, high quality.
```

## Visual Characteristics

- **Medium**: Watercolor with visible paper texture and soft edges
- **Brushstrokes**: Loose and organic, not photorealistic
- **Colors**: Warm earth tones, soft pastels, gentle saturation
- **Lighting**: Soft, diffused light (golden hour, warm glow)
- **Characters**: Rounded, friendly features with expressive eyes
- **Backgrounds**: Atmospheric with depth, slightly softer than foreground
- **Mood**: Cozy, warm, inviting

## Character Consistency Tips

The current pipeline solves character consistency by **anchoring every scene
to a per-character reference portrait** generated once in the `portraits`
stage, then passed as a reference image to every scene call in `illustrate`
(via Nano Banana / Gemini Flash Image). Identity locking is the model's job,
not the prompt's.

When writing scene illustration prompts in the `write` stage:

1. **Refer to characters by name + one short identifier** — "Freddie (sandy
   hair, blue jacket)" is enough; the reference portrait carries the rest.
2. **Describe the scene, not the character anatomy** — pose, action, setting,
   mood, lighting. The portrait locks the face/build; don't fight it with
   conflicting clothing details unless the story explicitly changes outfits.
3. **Use specific identifying features only for callouts** — "still wearing
   the red scarf" is useful; "a small brown bear cub with a red scarf and
   tiny round nose and..." is wasted tokens.
4. **Mood and composition matter** — "looking up with wide curious eyes from
   a low angle" steers the *scene*, not the *identity*.
5. **No-character scenes** (landscapes, abstract title cards) don't need
   references — they fall through to the text-only path.

Legacy advice for text-only providers (Leonardo path, no portraits) — only
needed if `image_provider=leonardo`: describe characters fully in every prompt,
specify exact colors and proportions, restate every scene.

## Alternative Styles

If the user's prompt suggests a different style, adapt accordingly:

| Story Tone | Suggested Style |
|------------|----------------|
| Dark/gothic | Ink wash with dramatic shadows |
| Sci-fi | Digital art with clean lines and neon accents |
| Whimsical | Colored pencil with playful line work |
| Realistic | Oil painting with rich detail |
| Retro | Vintage poster art with limited palette |
| Fantasy | Luminous digital painting with magical lighting |
