include("agents.jl")
using Genie, Genie.Renderer.Json, Genie.Requests, HTTP, Logging
using UUIDs

# --------- Modelo ---------
@info "Inicializando modelo..."
model = initialize_model()
@info "Modelo creado con éxito."

# throttling del step
last_step_time = time()
step_interval = 0.10   # 100 ms

# --------- CORS (real, incluye OPTIONS) ---------
Genie.config.run_as_server = true
Genie.config.cors_headers["Access-Control-Allow-Origin"] = "*"
Genie.config.cors_headers["Access-Control-Allow-Headers"] = "Content-Type"
Genie.config.cors_headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
Genie.config.cors_allowed_origins = ["*"]

route("/", method=OPTIONS) do
    HTTP.Response(200)
end
route("/*", method=OPTIONS) do
    HTTP.Response(200)
end

# --------- Rutas ---------
route("/init_keys", method = POST) do
    try
        payload = jsonpayload()
        key_positions = payload["keys"]::Vector
        global model
        model = initialize_model(key_positions=[(Int(k[1]), Int(k[2])) for k in key_positions])
        @info "Llaves inicializadas (ESCONDIDAS): $key_positions"
        json(Dict("status" => "ok", "keys" => key_positions))
    catch e
        @error "Error en /init_keys" exception=e
        json(Dict("error" => string(e)))
    end
end

route("/reveal_key", method = POST) do
    try
        p = jsonpayload()
        key_pos = (Int(p["x"]), Int(p["y"]))
        for a in allagents(model)
            if a isa Key && a.pos == key_pos && a.is_hidden
                a.is_hidden = false
                a.is_visible = true
                @info "Llave $key_pos → VISIBLE"
                break
            end
        end
        json(Dict("status" => "ok"))
    catch e
        @error "Error en /reveal_key" exception=e
        json(Dict("error" => string(e)))
    end
end

route("/collect_key", method = POST) do
    try
        p = jsonpayload()
        key_pos = (Int(p["x"]), Int(p["y"]))
        for a in allagents(model)
            if a isa Key && a.pos == key_pos
                a.is_visible = false
                a.is_collected = true
                @info "Llave $key_pos → RECOLECTADA"
                break
            end
        end
        json(Dict("status" => "ok"))
    catch e
        @error "Error en /collect_key" exception=e
        json(Dict("error" => string(e)))
    end
end

route("/update") do
    try
        global last_step_time
        now = time()
        if now - last_step_time >= step_interval
            step!(model, 1)
            last_step_time = now
        end
        ghosts = [Tuple(a.pos) for a in allagents(model) if a isa Ghost]
        keys   = [Tuple(a.pos) for a in allagents(model) if a isa Key && a.is_visible && !a.is_collected]
        json(Dict("ghosts" => ghosts, "keys" => keys))
    catch e
        @error "Error en /update" exception=e
        json(Dict("error" => string(e)))
    end
end

route("/status") do
    try
        ghosts = [Tuple(a.pos) for a in allagents(model) if a isa Ghost]
        keys_visible   = [Tuple(a.pos) for a in allagents(model) if a isa Key && a.is_visible && !a.is_collected]
        keys_hidden    = [Tuple(a.pos) for a in allagents(model) if a isa Key && a.is_hidden]
        keys_collected = [Tuple(a.pos) for a in allagents(model) if a isa Key && a.is_collected]
        json(Dict(
            "ghosts" => ghosts,
            "keys_visible" => keys_visible,
            "keys_hidden" => keys_hidden,
            "keys_collected" => keys_collected
        ))
    catch e
        @error "Error en /status" exception=e
        json(Dict("error" => string(e)))
    end
end

@info "Servidor iniciando en puerto 8000..."
up(8000, host="0.0.0.0")