#webapi.jl

include("agents.jl")
using Genie, Genie.Renderer.Json, Genie.Requests, HTTP, Logging
using UUIDs

@info "Inicializando modelo..."
model = initialize_model()
@info "Modelo creado con éxito."

last_step_time = time()

step_interval = 0.60  

Genie.config.run_as_server = true
Genie.config.cors_headers["Access-Control-Allow-Origin"] = "*"
Genie.config.cors_headers["Access-Control-Allow-Headers"] = "Content-Type"
Genie.config.cors_headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
Genie.config.cors_allowed_origins = ["*"]

route("/", method="OPTIONS") do
    return HTTP.Response(200, Genie.config.cors_headers)
end
route("/*", method="OPTIONS") do
    return HTTP.Response(200, Genie.config.cors_headers)
end

#  Rutas 
route("/init_keys", method = POST) do
    try
        payload = jsonpayload()
        
        key_positions = payload["keys"] 
        
        global model
        coords = [(Int(k[1]), Int(k[2])) for k in key_positions]
        
        model = initialize_model(key_positions=coords)
        
        for agent in allagents(model)
            if agent isa Ghost
                agent.is_evil = false
                agent.has_key = false
            end
        end

        @info "♻️ REINICIO TOTAL: Modelo recreado con $(length(coords)) llaves."
        json(Dict("status" => "ok"))
    catch e
        @error "Error en /init_keys" exception=e
        json(Dict("error" => string(e)))
    end
end

route("/trigger_evil", method = POST) do
    try
        global model
        found = false
        for a in allagents(model)
            if a isa Ghost
                a.is_evil = true
                found = true
                @info "¡MALDICIÓN ACTIVADA! El fantasma ahora busca llaves."
            end
        end
        json(Dict("status" => "ok", "found" => found))
    catch e
        @error "Error en /trigger_evil" exception=e
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
                @info "Jugador recogió llave en $key_pos"
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
        
        # Solo avanzamos 1 paso si ha pasado el tiempo (0.6 segundos)
        if now - last_step_time >= step_interval
            step!(model, 1)
            last_step_time = now
        end

        ghost_data = []
        for a in allagents(model)
            if a isa Ghost
                push!(ghost_data, Dict(
                    "pos" => Tuple(a.pos), 
                    "is_evil" => a.is_evil
                ))
            end
        end

        # filtración de llaves: si el fantasma se la comió is_visible=false
        keys = [Tuple(a.pos) for a in allagents(model) if a isa Key && a.is_visible && !a.is_collected]
        
        json(Dict("ghosts" => ghost_data, "keys" => keys))

    catch e
        @error "Error en /update" exception=e
        json(Dict("error" => string(e)))
    end
end

@info "Servidor listo en puerto 8000. Velocidad de fantasma ajustada."
up(8000, host="0.0.0.0")