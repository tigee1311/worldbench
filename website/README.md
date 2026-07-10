# WorldBench Website

Static source for [worldbench.xyz](https://worldbench.xyz), deployed with Vercel.

## Local preview

```bash
cd website
python3 -m http.server 4173
```

Then open `http://127.0.0.1:4173`.

Validate and build the deployable static bundle:

```bash
npm run build
```

## Production deploy

From this directory, run:

```bash
vercel --prod --yes
```

The deployable bundle uses the checked-in checkpoint-proof screenshots under
`website/assets/screenshots/`:

```bash
cd website
npm run build
```
