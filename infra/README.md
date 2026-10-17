# Infraestructura

La web corre en Vercel y la API en AWS Lambda (cuenta del perfil `default`, región
`us-east-1`). Todo lo de AWS lleva el tag `Project=ya-sale`.

## Qué se crea

```
yasale.cuisangelo.com ──► Vercel (web estática de web/out)
                            └─ /api/*, /mcp ──► Lambda Function URL (streaming)
                                                  └─► subredes privadas
                                                        ├─► RDS Postgres 16 (db.t4g.micro, privado)
                                                        └─► NAT gateway ──► Tavily, Exa, Claude, Google
```

- **Web:** proyecto `ya-sale` de Vercel conectado a GitHub, con raíz `web/` y salida `out`.
  `web/vercel.json` reenvía `/api` y `/mcp` a la Function URL, así la web y la API comparten
  dominio.
- **API:** función `ya-sale-api`, imagen de contenedor con Lambda Web Adapter. Tiene 2 GB y
  300 s, y la Function URL usa `RESPONSE_STREAM` para el SSE de los viajes. La concurrencia
  está reservada en 10: tope de costo y de conexiones (4 por instancia).
- **Base privada:** RDS sin acceso público. Su security group solo acepta el puerto 5432
  desde el security group `ya-sale-connector`, que es el de la función.
- **Salida a internet:** un NAT gateway, para que la función llegue a las APIs externas.
- **Secretos:** las claves y el `DATABASE_URL` viven en SSM Parameter Store (`/ya-sale/*`,
  SecureString). `lambda.sh` los copia como variables de entorno de la función, que Lambda
  guarda cifradas. Ningún script imprime un secreto.
- **Imagen:** ECR `ya-sale`, con escaneo al subir.
- **CD:** GitHub Actions asume el rol `ya-sale-github-deploy` por OIDC, solo desde `main`. El
  rol solo puede subir a ECR y actualizar `ya-sale-api`. El job compara `main` con el commit
  de la imagen viva y despliega solo si cambió `backend/`, `Dockerfile` o `infra/`.

## Pasos

```bash
bash infra/setup.sh             # una vez: red, base, ECR, security groups, sal de huellas
bash infra/secrets.sh           # cuando backend/.env tenga las claves y la base esté lista
bash infra/lambda.sh <imagen>   # una vez, o al cambiar secretos: función, entorno, URL
bash infra/github-oidc.sh       # una vez: rol de deploy para GitHub Actions
bash infra/deploy.sh <tag>      # deploy manual: build, push, actualizar la función, smoke test
```

Un push a `main` despliega solo. Push a producción en ~1,5 min, con un arranque en frío
de unos 20 s en la primera llamada.

## Costo aproximado

- NAT gateway: unos USD 1,1 por día, más el tráfico.
- RDS `db.t4g.micro`: unos USD 0,4 por día.
- Lambda: por uso. Sin tráfico no cobra.
- Vercel (plan gratuito), SSM estándar y ECR: centavos o nada.

## Después del evento

Borrar el NAT gateway (y liberar su IP elástica) y la instancia RDS, que cobran por hora.
Después, la función, la Function URL y el servicio pausado de App Runner `ya-sale`.
